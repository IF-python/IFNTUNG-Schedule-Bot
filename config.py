import os

import pytz
import redis
from mixpanel import Mixpanel

TIMEOUT = 10000
CACHE_TIME = 3600 * 10  # 10 hours
TIME_ZONE = pytz.timezone('Europe/Kiev')
DEFAULT_ENCODING = 'windows-1251'
URL = 'http://194.44.112.6/cgi-bin/timetable.cgi?n=700'
TIMESTAMP_LENGTH = 12
DAYS = {'Сьогодні': 0, 'Завтра': 1}
REQUESTS_LIMIT_PER_DAY = 25
THROTTLE_TIME = 2
mp = Mixpanel(os.environ.get('MIX_TOKEN'))
redis_storage = redis.from_url(os.environ.get('REDIS_URL'))
FLAG_MESSAGE = 'Військова підготовка'
DEFAULT_TIME_SET = ['6:00', '6:15', '6:30', '6:45', '7:00', '7:15', '7:30', '7:45', '8:00']
