suggest_message = 'Групу не здайдено, можливо ви мали на увазі:'
group_not_found = 'Групу не знайдено, спробуйте знову:'
info_message = '''
Users: {}\nSource code: [click](https://github.com/P-Alban/IFNTUNG-Schedule-Bot)
[Schedule API](https://www.ifntung-api.com/apidocs/)\n
_Ви можете відправляти 25 запитів розкладу на добу але не частіше ніж раз в 2 секунди._\n
*У вас залишилось {}/25 запитів на сьогодні.*

/get - Показати мою групу
/set - Змінити групу
/chair - Змінити кафедру
/notify - Нагадування
'''
set_group_message = '''Ви обрали: {} ({})

Якщо Ви навчаєтесь на Воєнній кафедрі, введіть команду /chair'''
not_found = 'Пар немає :)'
response_format = '*(№{}) Початок: {}. Кінець: {}*.\n{}\n\n'
pretty_format = '*Дата: {}. {} пар(и). {}.*\n\n{}'
tip_message = 'Відправте команду /date [DATE]. Наприклад:\n /date 05.09.2018'
group_info = 'Ваша група: {name} ({code})'
chair_info = '''
Якщо параметр "Воєнна кафедра" рівний `True`, це означає що Вам буде доступний тільки розклад Військової підготовки.

Якщо цей параметр рівний `False`, Вам буде доступний загальний розклад (без Військової підготовки)

*Воєнна кафедра: {}*
'''
notify_template = '''
Ви можете вказати час в який Вам буде приходити розклад на поточний день.
Сповіщення будуть надходити з понеділка по п\'ятницю.

*Встановлений час: {}*

_Дана функція в режимі тестування, тому якщо замітите неточності одразу пишіть:_ @PavelDurmanov
'''
time_menu_template = 'Оберіть час з меню або вкажіть вручну в форматі HH:MM, наприклад 10:45.'
