import os

import redis
from mixpanel import Mixpanel

TIMEOUT = 10000
default_encoding = 'windows-1251'
url = 'http://194.44.112.6/cgi-bin/timetable.cgi?n=700'
timestamp_length = 11
days = {'Сьогодні': 0, 'Завтра': 1}
requests_limit_per_day = 25
throttle_time = 2
mp = Mixpanel(os.environ.get('MIX_TOKEN'))
r = redis.from_url(os.environ.get('REDIS_URL'))
