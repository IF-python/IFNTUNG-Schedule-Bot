import re
import os
import json
import redis
import models
import logging
import calendar
import requests
import datetime as dt
from lxml import html
from functools import wraps
from collections import namedtuple
from mixpanel import Mixpanel, MixpanelException

logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-2s [%(asctime)s] %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('worker')
mp = Mixpanel(os.environ.get('MIX_TOKEN'))
suggest_message = 'Групу не здайдено, можливо ви мали на увазі:'
group_not_found = 'Групу не знайдено, спробуйте знову:'
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


def from_cache(func):
    @wraps(func)
    def wrapper(first, group):
        schedule = r.get('schedule::{}'.format(group))
        if not schedule:
            result = func(first, group)
            r.set('schedule::{}'.format(group), result, ex=3600)
            return result
        print('from cache')
        return schedule
    return wrapper


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


@from_cache
def from_string(date, group):
    try:
        current_date = dt.datetime.strptime(date, '%d.%m.%Y')
        verbose_day = calendar.day_name[current_date.weekday()]
        return parse(date, verbose_day, group)
    except ValueError:
        return 'Хибний формат дати.'


@from_cache
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
