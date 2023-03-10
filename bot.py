import logging
import os
import textwrap
from typing import List

from dotenv.main import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)

import settings
from reservations import (Reservation, add_chat_id, add_reservation,
                          delete_reservation, edit_reservation,
                          get_chat_id_list, show_reservations_all,
                          show_reservations_archive,
                          show_reservations_per_date, show_reservations_today)
from validators import InvalidDatetimeException

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    exit('No TG token found!')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# states for /addreserve conversation
GUEST_NAME, DATE_TIME, MORE_INFO, CHOICE, CANCEL, END = range(6)
# states for edit conversation
EDIT_NAME, EDIT_DATETIME, EDIT_INFO = range(3)
# state for reserves_per_date conversation
ENTER_THE_DATE = 1

# клавиатура для карточек резервов
RESERVE_CARD_KEYBOARD = [
        [InlineKeyboardButton('Гости пришли', callback_data='visited')],
        [
            InlineKeyboardButton(
                'Удалить бронь', callback_data='delete_reservation'
            ),
            InlineKeyboardButton(
                'Изменить бронь', callback_data='edit_reservation'
            ),
        ],
        [InlineKeyboardButton('Для копирования', callback_data='copy_format')]
    ]


# базовая клавиатура с командами бота
BASE_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            settings.NEW_RESERVE_BUTTON,
            settings.TODAY_RESERVES_BUTTON
        ],
        [
            settings.ARCHIVE_BUTTON,
            settings.ALL_RESERVES_BUTTON,
            settings.RESERVES_PER_DATE_BUTTON
        ],
        [
            settings.HELP_BUTTON
        ]
    ],
    resize_keyboard=True
    )


async def send_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_text: str,
    reply_markup: ReplyKeyboardMarkup or ReplyKeyboardRemove or InlineKeyboardMarkup = ReplyKeyboardRemove(),
):
    """Шорткат для отправки сообщения в текущий чат"""
    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def notify_all_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_text: str
):
    """Функция отправляет всем пользователям бота
    сообщение с переданной информацией"""
    for chat_id in get_chat_id_list():
        if chat_id == update.effective_chat.id:
            pass
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg_text,
                reply_markup=None
            )
    await send_message(update, context,
                       settings.NOTIFY_ALL_CONFIRMATION,
                       reply_markup=None)


async def keyboard_off(update: Update):
    """Шорткат для удаления клавиатуры у текущего сообщения"""
    await update.callback_query.edit_message_text(
        text=update.effective_message.text,
    )


async def create_update_msg_reservation_link(
    msg_id: int,
    reservation: Reservation,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Шорткат для обновления связки сообщение-объект резерва или добавления новой"""
    context.chat_data['msg_reservation'].update({msg_id: reservation})


async def get_reservation_from_msg(
    msg_id: int,
    context: ContextTypes.DEFAULT_TYPE
):
    """Шорткат для получения объекта резерва по id сообщения"""
    return context.chat_data['msg_reservation'][msg_id]


async def reservations_to_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reservations: List[Reservation]
) -> None:
    """Функция принимает список с резервами и отправляет сообщение
     за каждый из элементов, добавляя к ним кнопки."""
    if len(reservations) == 0:
        await send_message(update, context, settings.NO_INFO_FOUND, reply_markup=BASE_KEYBOARD)
    elif len(reservations) > settings.NUMBER_OF_RESERVES_BEFORE_LIST:
        keyboard = []
        for reservation in reservations:
            keyboard.append([
                InlineKeyboardButton(
                    reservation.reserve_line(logs=False),
                    callback_data=reservation
                )
            ])

        await send_message(
                update,
                context,
                'Вот что я нашел:',
                reply_markup=BASE_KEYBOARD
                )
        await send_message(
                update,
                context,
                'Резервы:',
                reply_markup=InlineKeyboardMarkup(keyboard)
                )
    else:
        await send_message(
                update,
                context,
                'Вот что я нашел:',
                reply_markup=BASE_KEYBOARD
                )
        for reservation in reservations:
            msg = await send_message(
                update,
                context,
                reservation.reserve_card(),
                InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD),
                )
            # словарь для связки объекта резерва с сообщением о нем
            context.chat_data.setdefault('msg_reservation', {}).update({msg.id: reservation})


async def delete_reserve_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция удаляет запись о брони из БД и выводит подтверждение в чат"""
    update.callback_query.answer()
    reservation = await get_reservation_from_msg(update.effective_message.id, context)
    delete_reservation(reservation)
    await update.callback_query.edit_message_text(
        text='ОТМЕНЕНА' + '\n' + reservation.reserve_card()
    )
    del context.chat_data['msg_reservation'][update.effective_message.id]
    logging.info('\nReservation deleted:\n{}'.format(reservation.reserve_line()))
    await notify_all_users(
        update,
        context,
        settings.NOTIFY_ALL_DELETE_RESERVE + '\n\n' + reservation.reserve_card()
    )
    return ConversationHandler.END


async def visited_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция обновляет информацию о приходе гостей в бд и изменяет карточку резерва"""
    update.callback_query.answer()
    reservation = await get_reservation_from_msg(update.effective_message.id, context)
    reservation.visited_on_off()
    edit_reservation(reservation)
    await update.callback_query.edit_message_text(
        text=reservation.reserve_card(),
        reply_markup=InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD)
    )
    await create_update_msg_reservation_link(update.effective_message.id, reservation, context)
    logging.info('\nGuests visit status changed:\n{}'.format(reservation.reserve_line()))
    return ConversationHandler.END


async def edit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает параметры резерва, которые можно изменить"""
    context.user_data['reservation'] = await get_reservation_from_msg(update.effective_message.id, context)
    # сохраняем id сообщения, из которого запущен процесс редактирования
    context.user_data['edited_id'] = update.effective_message.id
    keyboard = [
        [InlineKeyboardButton('Имя', callback_data='edit_name')],
        [InlineKeyboardButton('Дата / Время', callback_data='edit_datetime')],
        [InlineKeyboardButton('Детали', callback_data='edit_info')],
    ]
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text='Что меняем?:' + '\n\n' + update.effective_message.text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def copy_format_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Функция изменяет сообщение и выводит информацию о резерве
    в удобном для копирования формате"""
    reservation = await get_reservation_from_msg(
        update.effective_message.id, context
    )
    await update.callback_query.edit_message_text(
        text=reservation.reserve_copy_card(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить имя в резерве"""
    await keyboard_off(update)
    await send_message(
        update,
        context,
        'Текущее имя в резерве: ' + context.user_data['reservation'].guest_name + '\n' + 'Отправь мне новое!'
    )
    context.user_data['changed'] = 'name'
    await update.callback_query.answer()


async def edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить время визита в резерве"""
    await keyboard_off(update)
    await send_message(
        update,
        context,
        'Текущее время визита в резерве: ' + str(context.user_data['reservation'].date_time.strftime(settings.DATETIME_FORMAT)) + '\n' + 'Отправь мне новое!'
    )
    context.user_data['changed'] = 'time'


async def edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить детали в резерве"""
    await keyboard_off(update)
    await send_message(
        update,
        context,
        'Детали: ' + context.user_data['reservation'].info + '\n' + 'На что меняем?'
    )
    context.user_data['changed'] = 'info'


async def edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет новую информацию и выводит обновленный резерв"""
    #узнаем что поменялось и сохраняем
    changed = context.user_data['changed']
    if changed == 'name':
        context.user_data['reservation'].guest_name = update.message.text
    elif changed == 'time':
        try:
            context.user_data['reservation'].date_time = Reservation.str_to_datetime(update.message.text)
        except InvalidDatetimeException as datetime_validation_error:
            await send_message(update, context, datetime_validation_error.args[0]) # вот это конечно сильно
            return EDIT_DATETIME
    elif changed == 'info':
        context.user_data['reservation'].info = update.message.text

    # получаем измененный резерв
    reservation = context.user_data['reservation']
    # изменяем его в ДБ
    edit_reservation(reservation)

    logging.info('\nReservation info changed:\n{}'.format(
        reservation.reserve_line())
    )
    msg = await send_message(
        update,
        context,
        reservation.reserve_card(),
        reply_markup=InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD)
    )
    await send_message(
        update,
        context,
        settings.RESERVER_ADDITION_END_SAVE,
        reply_markup=BASE_KEYBOARD)
    await notify_all_users(
        update,
        context,
        settings.NOTIFY_ALL_EDIT_RESERVE + f'({changed})' + '\n\n' + reservation.reserve_card()
    )
    await create_update_msg_reservation_link(msg.id, reservation, context)
    return ConversationHandler.END


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор кнопочек"""
    query = update.callback_query
    await query.answer()
    try:
        if query.data == 'delete_reservation':
            await delete_reserve_button(update, context)
        if query.data == 'edit_reservation':
            await edit_button(update, context)
        if query.data == 'visited':
            await visited_button(update, context)
        if query.data == 'copy_format':
            await copy_format_button(update, context)
        if query.data == 'edit_name':
            await edit_name(update, context)
            return EDIT_NAME
        if query.data == 'edit_datetime':
            await edit_time(update, context)
            return EDIT_DATETIME
        if query.data == 'edit_info':
            await edit_info(update, context)
            return EDIT_INFO
        if isinstance(query.data, Reservation):
            await reservations_to_messages(update, context, [query.data, ])
    except KeyError:
        await send_message(update, context, settings.CARD_BUTTONS_ERROR_MSG)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    current_chat_id = update.effective_chat.id
    if current_chat_id not in get_chat_id_list():
        add_chat_id(current_chat_id)
        logging.info(f'New person pressed /start: {update.effective_user.name}')

    await send_message(
        update,
        context,
        settings.GREETINGS,
        reply_markup=BASE_KEYBOARD
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    await send_message(
        update,
        context,
        settings.HELP,
        reply_markup=BASE_KEYBOARD
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /cancel"""
    context.user_data.clear()
    await send_message(
        update,
        context,
        '🙅‍♂️ Отменил 🙅‍♂️',
        reply_markup=BASE_KEYBOARD)
    return ConversationHandler.END


async def archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /archive. Выводит резервы раньше текущей даты"""
    await reservations_to_messages(update, context, show_reservations_archive())


async def allreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /allreserves. Выводит резервы позже текущей даты"""
    await reservations_to_messages(update, context, show_reservations_all())


async def todayreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /todayreserves. Выводит резервы на текущий день"""
    await reservations_to_messages(update, context, show_reservations_today())


async def addreserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог о записи резерва и спрашивает имя гостя"""
    context.user_data['new_reservation'] = Reservation()
    await send_message(update, context, settings.RESERVER_ADDITION_START)
    await send_message(
        update, context, settings.RESERVER_ADDITION_GUEST_NAME
    )
    return GUEST_NAME


async def guest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает имя гостя и запрашивает дату и время визита"""
    context.user_data['new_reservation'].guest_name = update.message.text
    await send_message( update, context, settings.RESERVER_ADDITION_TIME)
    return DATE_TIME


async def date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дату и время визита и запрашивает дополнительную информацию"""
    try:
        context.user_data['new_reservation'].date_time = Reservation.str_to_datetime(update.message.text)
    except InvalidDatetimeException as datetime_validation_error:
        await send_message(update, context, datetime_validation_error.args[0]) # вот это конечно сильно
        return DATE_TIME
    await send_message(update, context, settings.RESERVER_ADDITION_MORE_INFO)
    return MORE_INFO


async def more_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дополнительную информацию.
    Выводит собраную информацию о брони с возможностью подтвердить / отменить запись"""
    context.user_data['new_reservation'].info = textwrap.dedent(update.message.text)
    reply_keyboard = [['Сохранить', 'Отмена']]

    await send_message(update, context, settings.RESERVER_ADDITION_SAVE_EDIT_DELETE)
    await send_message(
        update, context,
        textwrap.dedent(context.user_data['new_reservation'].reserve_preview()),
        ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder='Шо делаем?',
            resize_keyboard=True,
        )
    )
    return CHOICE


async def cancel_new_reserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет сбор данных о новом резерве"""
    context.user_data.clear()
    await send_message(update, context, '🙅‍♂️ Отменил 🙅‍♂️')
    return ConversationHandler.END


async def end_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет запись и заканчивает сбор данных"""
    context.user_data['new_reservation'].user_added = update.effective_user.name
    reservation = context.user_data['new_reservation']
    add_reservation(reservation)
    logging.info('\nReservation saved:\n{}'.format(reservation.reserve_line()))
    await reservations_to_messages(update, context, [reservation, ])
    await send_message(
        update,
        context,
        settings.RESERVER_ADDITION_END_SAVE,
        reply_markup=BASE_KEYBOARD)
    await notify_all_users(
        update,
        context,
        settings.NOTIFY_ALL_NEW_RESERVE + '\n\n' + reservation.reserve_card()
    )
    del context.user_data['new_reservation']
    return ConversationHandler.END


async def reserves_per_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки выдачи резервов по дате. Запрашивает дату."""
    await send_message(
        update,
        context,
        settings.ASK_FOR_DATE,
    )
    return ENTER_THE_DATE


async def reserves_per_date_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет запись и заканчивает сбор данных"""
    try:
        await reservations_to_messages(
            update, context,
            show_reservations_per_date(Reservation.str_to_date(update.message.text))
        )
    except InvalidDatetimeException as datetime_validation_error:
        await send_message(update, context, datetime_validation_error.args[0]) # вот это конечно сильно
        return ENTER_THE_DATE
    return ConversationHandler.END


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).arbitrary_callback_data(True).build()

    # Добавляем обработку команды /start
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Добавляем обработку команды /archive
    archive_handler = MessageHandler(
        filters.Regex(f'^{settings.ARCHIVE_BUTTON}$'),
        archive
    )
    application.add_handler(archive_handler)

    # Добавляем обработку команды /help
    help_handler = MessageHandler(
        filters.Regex(f'^{settings.HELP_BUTTON}$'),
        help_command
    )
    application.add_handler(help_handler)

    # Добавляем обработку команды /allreserves
    allreserves_handler = MessageHandler(
        filters.Regex(f'^{settings.ALL_RESERVES_BUTTON}$'),
        allreserves
    )
    application.add_handler(allreserves_handler)

    # Добавляем обработку команды /todayreserves
    todayreserves_handler = MessageHandler(
        filters.Regex(f'^{settings.TODAY_RESERVES_BUTTON}$'),
        todayreserves
    )
    application.add_handler(todayreserves_handler)

    # Добавляем обработку команды /addreserve
    addreserve_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f'^{settings.NEW_RESERVE_BUTTON}$'),
                addreserve
            )
        ],
        states={
            GUEST_NAME: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), guest_name)
            ],
            DATE_TIME: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), date_time)
            ],
            MORE_INFO: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), more_info)
            ],
            CHOICE: [
                MessageHandler(filters.Regex('^Сохранить$'), end_save),
                MessageHandler(filters.Regex('^Отмена$'), cancel_new_reserve),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(addreserve_handler)

    # Добавляем обработку запроса на редактирование резерва
    editreserve_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button),
        ],
        states={
            EDIT_NAME: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), edit_save)
            ],
            EDIT_DATETIME: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), edit_save)
            ],
            EDIT_INFO: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), edit_save)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(editreserve_handler)

    # Добавляем обработку нажатия кнопки выдачи резервов по дате
    reserves_per_date_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f'^{settings.RESERVES_PER_DATE_BUTTON}$'),
                reserves_per_date_command
            )
        ],
        states={
            ENTER_THE_DATE: [
                MessageHandler(
                    filters.TEXT & (~ filters.COMMAND),
                    reserves_per_date_answer
                )
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(reserves_per_date_handler)

    # Поллинг
    application.run_polling()


if __name__ == '__main__':
    main()
