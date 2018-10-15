import json
from models import Group

# insert groups into database
from_json = json.load(open('groups.json', encoding='utf8'))
for key, value in from_json.items():
    Group.create(group_code=key, verbose_name=value)
