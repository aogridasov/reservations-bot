# Reservations Bot

Reservations Bot это телеграм-бот, который помогает записывать информацию о бронировании столов и отслеживать её в удобном формате.
Проект был реализован для автоматизации рутинных процессов в реальной точке общепита.

**Технологии:** Python, [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot), sqlite 

## Установка

### Версии стека
Подробнее в requirements.txt
```
Python 3.7.9
python-telegram-bot 20.0
``` 

### Деплой
Клонировать репозиторий и перейти в него в командной строке:
```
git clone git@github.com:aogridasov/reservations-bot.git
``` 
Установить и активировать виртуальное окружение:
``` 
python -m venv env
source env/bin/activate
```
Установить зависимости из файла requirements.txt:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
``` 
Запустить файл, создающий базу данных:
```
python create_reservations_db.py
```
Запустить бота:
```
python bot.py
```

## Дополнительно

### Справка по взаимодействию с ботом
📖Для добавления бронирования воспользуйтесь кнопкой "Новое бронирование"  
"Бронирования на сегодня" выведет все бронирования на текущий день.  
"Все бронирования" выведет все бронирования, начиная с текущего дня.  
"Старые бронирования" выведет все бронирования, с временем визита раньше текущего момента.  

Информацию о резервах можно менять, используя кнопки, прилегающие к сообщению с резервом.  

❗ Подтверждение добавления резерва и любые подтвержденные изменения (кроме кнопки 'Гости пришли') приводят к оповещению всех пользователей бота.  

🤖 Полезные команды, которые можно отправить боту  
/cancel - прервет диалог о внесении информации по резерву  
/start - выведет приветственное сообщение и кнопки взаимодействия с ботом  

🕧 Ввод времени визита  
Бот еще совсем маленький и плохо умеет работать с датами и временем.  
Поэтому пожалуйста отправляйте дату исключительно в таком формате:  
01.03.2023 12:00  
Другие варианты он не пропустит. Так же не принимаются резервы "из прошлого".  
Время не должно быть раньше текущего момента.  

### База данных
БД реализованна на встроенном в python sqlite3 и содержит всего две не связанные таблицы: таблица с информацией о бронированиях и таблица с id чатов пользователей с ботом (для оповещений).

### settings.py
settings.py - файл с константами, содержащими названия кнопок, текст большинства сообщений бота, формат даты и другие настройки.

### TO DO LIST
- Аутентификация пользователей, имеющих доступ к боту
- Возможность выбирать конкретную дату, за которую будут отоброжаться бронирования.
- user-friendly способ передачи даты и времени
- Админ команды для работы с settings.py без преостановки работы бота
- Возможность добавлять отзывы пользователей в каждом бронировании
