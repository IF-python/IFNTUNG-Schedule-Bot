import calendar
import datetime as dt
import json
import logging
import re
import threading
from collections import namedtuple
from functools import wraps

import requests
from lxml import html
from mixpanel import MixpanelException

import models
from config import *
from templates import *

logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-2s [%(asctime)s] %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('worker')  # TODO fix this shit
CLASS = namedtuple('CLASS', ['from_time', 'to_time', 'rest', 'num'])
filtered = namedtuple('Filtered', ['index', 'rest', 'data'])
xpath = '//*[@id="wrap"]/div/div/div/div[3]/div[1]/div[1]/table'
s_time, e_time, rest = slice(1, 6), slice(6, 11), slice(11, None)
pattern = re.compile(r'\s{3,}')


def track(user, message):
    try:
        mp.track(str(user), message)
    except MixpanelException:
        logger.error('Mix panel track failed')


def validate_time(time):
    try:
        return dt.datetime.strptime(time, '%H:%M')
    except ValueError:
        return False


def get_cached_groups():
    groups = r.get('groups')
    if not groups:
        g = models.Group.get_all_groups()
        r.set('groups', json.dumps(g))
        return g
    return json.loads(groups)


def get_ttl():
    now = dt.datetime.now(TIME_ZONE)
    enf_of_the_day = TIME_ZONE.localize(dt.datetime.combine(now, dt.time.max))
    return int((enf_of_the_day - now).total_seconds())


def get_cache_time():
    ttl = get_ttl()
    return ttl if ttl < CACHE_TIME else CACHE_TIME


def get_requests_count(user_id):
    return r.get(f'limit::{user_id}') or 0


def in_thread(func):
    @wraps(func)
    def decorator(message):
        thread = threading.Thread(target=func, args=(message,))
        thread.start()

    return decorator


def limit_requests(func):
    @wraps(func)
    def decorator(message):
        user_id = message.from_user.id
        user_request_count = get_requests_count(user_id)
        if int(user_request_count) < REQUESTS_LIMIT_PER_DAY:
            r.set(f'limit::{user_id}', int(user_request_count) + 1, ex=get_ttl())
            return func(message)
        track(str(user_id), 'Reached requests limit')

    return decorator


def throttle(time=THROTTLE_TIME):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            user_id = message.from_user.id
            throttle_value = r.set(f'throttle::{user_id}', True, ex=time, nx=True)
            if throttle_value:
                return func(message)
            track(str(user_id), 'Throttle')

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
        current_date = dt.datetime.strptime(date, '%d.%m.%Y')
        verbose_day = calendar.day_name[current_date.weekday()]
        return parse(date, verbose_day, group, flag)
    except ValueError:
        return 'Хибний формат дати.'


def cached(func):
    @wraps(func)
    def wrapper(day, group, bot, user, extended_flag):
        from_cache = r.get(f'schedule::{day}::{extended_flag}::{group}')
        if not from_cache:
            bot.send_chat_action(user, 'typing')
            result = func(day, group, flag=extended_flag)
            r.set(f'schedule::{day}::{extended_flag}::{group}',
                  result, ex=get_cache_time())
            return result
        return from_cache

    return wrapper


@cached
def get_schedule(day, group, bot=None, user=None, flag=None):
    current_date = dt.datetime.date(dt.datetime.now())
    current_date += dt.timedelta(days=DAYS[day])
    return parse(current_date.strftime('%d.%m.%Y'), calendar.day_name[current_date.weekday()], group, flag)


def get_raw_content(date, group):
    payload = {
        'group': group.encode(DEFAULT_ENCODING),
        'edate': date,
        'sdate': date
    }
    response = requests.post(URL, data=payload)
    response.encoding = DEFAULT_ENCODING
    return response.text


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
                raw = raw.replace(FLAG_MESSAGE, '')
            yield filtered(index, raw, element)


def switcher(flag_value):
    return with_extended_flag if flag_value else without_extended_flag


def collect_tuples(data, date, verbose_day, flag):
    result = []
    filter_function = switcher(flag)
    for element in filter_function(data):
        if len(element.data) > TIMESTAMP_LENGTH:
            result.append(CLASS(element.data[s_time], element.data[e_time], pattern.sub('\n', element.rest),
                                element.index))
    return make_response(result, date, len(result), verbose_day)


def make_response(data, date, count, verbose_day):
    if not data:
        return not_found
    response = ''.join([response_format.format(x.num, x.from_time, x.to_time, x.rest) for x in data])
    return pretty_format.format(date, count, verbose_day, response.replace('`', '"'))  # prevent markdown error
