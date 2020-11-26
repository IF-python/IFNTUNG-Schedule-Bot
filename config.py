import os

import pytz
import redis
import sentry_sdk

sentry_sdk.init(
    os.getenv("SENTRY_SDK"),
    traces_sample_rate=1.0
)

TIMEOUT = 10000
CACHE_TIME = 3600 * 6  # 6 hours
TIME_ZONE = pytz.timezone("Europe/Kiev")
DEFAULT_ENCODING = "windows-1251"
URL = os.getenv("SCHEDULE_URL")
TIMESTAMP_LENGTH = 12
DAYS = {"Сьогодні": 0, "Завтра": 1}
REQUESTS_LIMIT_PER_DAY = 40
THROTTLE_TIME = 3
AMPLITUDE_KEY = os.getenv("AMPLITUDE_KEY")
redis_storage = redis.Redis(host="bot_redis", port=6379)
FLAG_MESSAGE = "Військова підготовка"
DEFAULT_TIME_SET = [
    "6:00",
    "6:15",
    "6:30",
    "6:45",
    "7:00",
    "7:15",
    "7:30",
    "7:45",
    "8:00",
]
DAY_NAMES = ["Понеділок", "Вівторок", "Середа", "Четвер", 'П"ятниця']
ADMIN_ID = 282213187
GROUPS_API = "https://www.ifntung-api.com/groups/exists?group={group}"
