import json
from openpyxl import load_workbook
from collections import namedtuple


path = r"C:\Users\alban\Desktop\exc.xlsx"
wb = load_workbook(path)
sheet = wb['Лист2']
group = namedtuple('Group', ['code', 'name'])
groups = [group(i[1], i[3]) for i in sheet.values if isinstance(i[0], int)]
json.dump(obj={item.code: item.name for item in groups},
          fp=open('groups.json', 'w', encoding='utf8'),
          indent=4, ensure_ascii=False)

