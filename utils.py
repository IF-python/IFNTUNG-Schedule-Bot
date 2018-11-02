import calendar
import datetime as dt
import json
import logging
import os
import re
from collections import namedtuple
from functools import wraps

import redis
import requests
from lxml import html
from mixpanel import Mixpanel, MixpanelException

import models

logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-2s [%(asctime)s] %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('worker')  # TODO fix this shit
mp = Mixpanel(os.environ.get('MIX_TOKEN'))
suggest_message = 'Групу не здайдено, можливо ви мали на увазі:'
group_not_found = 'Групу не знайдено, спробуйте знову:'
info_message = 'Users: {}\nSource code: [click](https://github.com/P-Alban/IFNTUNG-Schedule-Bot)'
set_group_message = 'Ви обрали: {} ({})'
r = redis.from_url(os.environ.get('REDIS_URL'))
TIMEOUT = 10000
default_encoding = 'windows-1251'
url = 'http://194.44.112.6/cgi-bin/timetable.cgi?n=700'
CLASS = namedtuple('CLASS', ['from_time', 'to_time', 'rest', 'num'])
xpath = '//*[@id="wrap"]/div/div/div/div[3]/div[1]/div[1]/table'
not_found = 'Розклад не знайдений.'
timestamp_length = 11
s_time, e_time, rest = slice(1, 6), slice(6, 11), slice(11, None)
pattern = re.compile(r'\s{3,}')
response_format = '*(№{}) Початок: {}. Кінець: {}*.\n{}\n\n'
pretty_format = '*Дата: {}. {} пар(и). {}.*\n\n{}'
days = {'Сьогодні': 0, 'Завтра': 1}
tip_message = 'Відправте команду /date [DATE]. Наприклад:\n /date 05.09.2018'
group_info = 'Ваша група: {name} ({code})'
requests_limit_per_day = 25


def track(user, message):
    try:
        mp.track(str(user), message)
    except MixpanelException:
        logger.error('Mix panel track failed')


def get_cached_groups():
    groups = r.get('groups')
    if not groups:
        g = models.Group.get_all_groups()
        r.set('groups', json.dumps(g))
        return g
    return json.loads(groups)


def limit_requests(func):
    @wraps(func)
    def decorator(message):
        user_id = message.from_user.id
        user_request_count = r.get(f'limit::{user_id}')
        if not user_request_count:
            r.set(f'limit::{user_id}', 1)
            return func(message)
        elif int(user_request_count) < requests_limit_per_day:
            r.set(f'limit::{user_id}', int(user_request_count) + 1)
            return func(message)
        track(str(user_id), 'Reached requests limit')
        return decorator


def throttle(func):
    @wraps(func)
    def decorator(message):
        user_id = message.from_user.id
        throttle_value = r.set(f'throttle::{user_id}', True,  ex=2, nx=True)
        if throttle_value:
            return func(message)
        track(str(user_id), 'Throttle')
    return decorator


def group_required(rollback):
    def decorator(func):
        @wraps(func)
        def wrapper(message):
            group = models.Student.has_group(message.from_user.id)
            if group:
                return func(message, group)
            return rollback(message)
        return wrapper
    return decorator


def from_string(date, group):
    try:
        current_date = dt.datetime.strptime(date, '%d.%m.%Y')
        verbose_day = calendar.day_name[current_date.weekday()]
        return parse(date, verbose_day, group)
    except ValueError:
        return 'Хибний формат дати.'


def cached(func):
    @wraps(func)
    def wrapper(day, group):
        from_cache = r.get(f'schedule::{day}::{group}')
        if not from_cache:
            result = func(day, group)
            r.set(f'schedule::{day}::{group}', result, ex=3600)
            return result
        return from_cache
    return wrapper


@cached
def get_schedule(day, group):
    current_date = dt.datetime.date(dt.datetime.now())
    current_date += dt.timedelta(days=days[day])
    return parse(current_date.strftime('%d.%m.%Y'), calendar.day_name[current_date.weekday()], group)


def get_raw_content(date, group):
    payload = {
        'group': group.encode(default_encoding),
        'edate': date,
        'sdate': date
    }
    response = requests.post(url, data=payload)
    response.encoding = default_encoding
    return response.text


def parse(date, verbose_day, group):
    tree = html.fromstring(get_raw_content(date, group)).xpath(xpath)
    if tree:
        content = [i.text_content() for i in tree[0].iterchildren()]
        return collect_tuples(content, date, verbose_day)
    return not_found


def collect_tuples(data, date, verbose_day):
    result = []
    for index, element in enumerate(data, 1):
        if len(element) > timestamp_length:
            result.append(CLASS(element[s_time], element[e_time], pattern.sub('\n', element[rest]), index))
    return make_response(result, date, len(result), verbose_day)


def make_response(data, date, count, verbose_day):
    response = ''.join([response_format.format(x.num, x.from_time, x.to_time, x.rest) for x in data])
    return pretty_format.format(date, count, verbose_day, response.replace('`', '"'))  # prevent markdown error
