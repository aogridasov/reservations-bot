# reservations-bot

ТЗ:

1. Приветственное сообщение: команды бота + хелп

2. Команды бота:
    /start - приветственное сообщение +
    /help - справка +
    /addreserve - добавить резерв +
    /todayreserves - вывести резервы на сегодня +
    /tomorrowreserves - вывести резервы на завтра
    /allreserves - вывести все резервы +
    /archivereserves - архив резервов

3. С 'карточкой' резерва можно взаимодействовать: редактировать / удалять / отмечать что пришли +

4. У резерва должны быть следующий атрибуты:
    - Имя гостя +
    - Дата и время визита
    - Дополнительная информация +
    - tg user добавивший резерв (автоматически) +
    - Пришел ли гость (bool, после создания) +

5. При добавлении / изменении / отмене существующего резерва присылается уведомление всем, контактирующим с ботом. +

6. Что потом нужно реализовать:
   - доступ только выбраным пользователям
   - прикрутить календарь к выбору даты
   - красивое меню с кнопками
