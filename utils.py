import calendar
import datetime as dt
import json
import logging
import telebot
import re
import threading
from collections import namedtuple
from functools import wraps

import requests
from dateutil.rrule import rrule, WEEKLY
from lxml import html
from mixpanel import MixpanelException

import models
from config import *
from templates import *

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
lesson = namedtuple("lesson", ["from_time", "to_time", "rest", "num"])
filtered = namedtuple("Filtered", ["index", "rest", "data"])
xpath = '//*[@id="wrap"]/div/div/div/div[4]/div[2]/div[1]/table'
s_time, e_time, rest = slice(1, 6), slice(6, 11), slice(11, None)
pattern = re.compile(r"\s{3,}")
date_format = "%d.%m.%Y"


def get_or_create_group(group_name):
    all_groups = get_cached_groups()
    return add_runtime_group(group_name) if group_name not in all_groups else True


def add_runtime_group(group_name):
    response = requests.get(GROUPS_API.format(group=group_name))
    if response.status_code == 200:
        logger.info(f"Group: {group_name} was added dynamically.")
        data = response.json()
        redis_storage.delete("groups")
        return models.Group.create(
            group_code=group_name, verbose_name=data["department"]
        )
    logger.warning(
        f"Group: {group_name} does not exists. Response code: {response.status_code}"
    )


def get_correct_day(day):
    offset = dt.datetime.today() + dt.timedelta(days=2)
    return rrule(WEEKLY, count=1, byweekday=day, dtstart=offset)[0]


def track(user, message):
    try:
        requests.post(
            "https://api.amplitude.com/2/httpapi",
            json={
                "api_key": AMPLITUDE_KEY,
                "events": [
                    {
                        "user_id": user,
                        "event_type": message
                    }
                ]
            }
        )
    except Exception:
        logger.exception("Amplitude panel track failed")


def validate_time(time):
    try:
        return dt.datetime.strptime(time, "%H:%M")
    except ValueError:
        return False


def get_cached_groups():
    groups = redis_storage.get("groups")
    if not groups:
        g = models.Group.get_all_groups()
        redis_storage.set("groups", json.dumps(g))
        return g
    return json.loads(groups)


def get_ttl():
    now = dt.datetime.now(TIME_ZONE)
    end_of_the_day = TIME_ZONE.localize(dt.datetime.combine(now, dt.time.max))
    return int((end_of_the_day - now).total_seconds())


def get_cache_time():
    ttl = get_ttl()
    return ttl if ttl < CACHE_TIME else CACHE_TIME


def get_requests_count(user_id):
    requests_count = redis_storage.get(f"limit::{user_id}")
    return int(requests_count) if requests_count else 0


def in_thread(func):
    @wraps(func)
    def decorator(message):
        thread = threading.Thread(target=func, args=(message,))
        thread.start()

    return decorator


def limit_requests(callback=None):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            user_id = message.from_user.id
            user_request_count = get_requests_count(user_id)
            if user_request_count < REQUESTS_LIMIT_PER_DAY:
                redis_storage.set(
                    f"limit::{user_id}", int(user_request_count) + 1, ex=get_ttl()
                )
                return func(message)
            track(user_id, "Reached requests limit")
            if callback:
                return callback(message)

        return wrapper

    return decorator


def throttle(time=THROTTLE_TIME):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            user_id = message.from_user.id
            throttle_value = redis_storage.set(
                f"throttle::{user_id}", True, ex=time, nx=True
            )
            if throttle_value:
                return func(message)
            track(user_id, "Throttle")

        return wrapper

    return decorator


def group_required(rollback):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            user = message.from_user.id
            group = models.Student.has_group(user)
            if group:
                return func(message, user, group)
            return rollback(message)

        return wrapper

    return decorator


def from_string(date, group, flag):
    try:
        current_date = dt.datetime.strptime(date, date_format)
        verbose_day = calendar.day_name[current_date.weekday()]
        return parse(date, verbose_day, group, flag)
    except ValueError:
        return "Хибний формат дати."


def cached(func):
    @wraps(func)
    def wrapper(day, group, bot, user, extended_flag):
        from_cache = redis_storage.get(f"schedule::{day}::{extended_flag}::{group}")
        if not from_cache:
            bot.send_chat_action(user, "typing")
            result = func(day, group, flag=extended_flag)
            if result != service_unavailable:
                ttl = get_cache_time()
                redis_storage.set(
                    f"schedule::{day}::{extended_flag}::{group}", result, ex=ttl
                )
            return result
        return from_cache.decode()

    return wrapper


def extract_result_from_redis(key, func, *args):
    from_cache = redis_storage.get(key)
    if not from_cache:
        result = func(*args)
        if result != service_unavailable:
            ttl = get_cache_time()
            redis_storage.set(key, result, ex=ttl)
        return result
    return from_cache.decode()


def weekday_cache(func):
    @wraps(func)
    def wrapper(date, group, flag):
        key = f"schedule::{date.strftime(date_format)}::{group}::{flag}"
        return extract_result_from_redis(key, func, date, group, flag)

    return wrapper


def read_timeout_rollback(func, retries=3):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for retry in range(retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException:
                logger.exception("Read timeout to telegram API #%s" % retry)
        return service_unavailable

    return wrapper


@weekday_cache
def week_day_schedule(date, group, flag):
    return parse(
        date.strftime(date_format), calendar.day_name[date.weekday()], group, flag
    )


@cached
def get_schedule(day, group, bot=None, user=None, flag=None):
    current_date = dt.datetime.date(dt.datetime.now(TIME_ZONE))
    current_date += dt.timedelta(days=DAYS[day])
    return parse(
        current_date.strftime(date_format),
        calendar.day_name[current_date.weekday()],
        group,
        flag,
    )


def get_raw_content(date, group):
    payload = {"group": group.encode(DEFAULT_ENCODING), "edate": date, "sdate": date}
    response = requests.post(URL, data=payload, timeout=1000)
    response.encoding = DEFAULT_ENCODING
    return response.text


@read_timeout_rollback
def parse(date, verbose_day, group, flag):
    tree = html.fromstring(get_raw_content(date, group)).xpath(xpath)
    if tree:
        content = [i.text_content() for i in tree[0].iterchildren()]
        return collect_tuples(content, date, verbose_day, flag)
    return not_found


def with_extended_flag(data):
    for index, element in enumerate(data, 1):
        if FLAG_MESSAGE in element[rest]:
            yield filtered(index, FLAG_MESSAGE, element)


def without_extended_flag(data):
    for index, element in enumerate(data, 1):
        raw = element[rest]
        if raw.strip() != FLAG_MESSAGE:
            if FLAG_MESSAGE in raw:
                raw = raw.replace(FLAG_MESSAGE, "")
            yield filtered(index, raw, element)


def switcher(flag_value):
    return with_extended_flag if flag_value else without_extended_flag


def collect_tuples(data, date, verbose_day, flag):
    result = []
    filter_function = switcher(flag)
    for element in filter_function(data):
        if len(element.data) > TIMESTAMP_LENGTH:
            text = pattern.sub("\n", element.rest)
            if "дистанційно" in text:
                text = text.replace("дистанційно", "Дистанційно\n")
            result.append(
                lesson(element.data[s_time], element.data[e_time], text, element.index)
            )
    return make_response(result, date, len(result), verbose_day)


def make_response(data, date, count, verbose_day):
    if not data:
        return not_found
    response = "".join(
        [response_format.format(x.num, x.from_time, x.to_time, x.rest) for x in data]
    )
    return pretty_format.format(
        date, count, verbose_day, response
    )
