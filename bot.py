import logging
import os
from typing import List, Dict
from uuid import uuid4

from dotenv.main import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InlineQueryResultArticle, InputTextMessageContent,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, ConversationHandler,
                          InlineQueryHandler, MessageHandler, filters)

import help_texts
from reservations import (DB_CONNECTION, DB_CURSOR, Reservation,
                          add_reservation, delete_reservation,
                          edit_reservation, show_reservations_all,
                          show_reservations_today)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    exit('No TG token found!')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# states for /addreserve conversation
GUEST_NAME, DATE_TIME, MORE_INFO, CHOICE, CANCEL, END = range(6)
# states for edit conversation
EDIT_NAME, EDIT_DATETIME, EDIT_INFO = range(3)

# клавиатура для карточек резервов
RESERVE_CARD_KEYBOARD = [
        [InlineKeyboardButton('Гости пришли', callback_data='visited')],
        [
            InlineKeyboardButton('Удалить бронь', callback_data='delete_reservation'),
            InlineKeyboardButton('Изменить бронь', callback_data=str('edit_reservation')),
        ],
    ]


async def send_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_text: str,
    reply_markup=ReplyKeyboardRemove(),
    reservation=None
):
    """Шорткат для отправки сообщения"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg_text,
        reply_markup=reply_markup,
    )


async def reservations_to_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reservations: List[Reservation]
) -> None:
    """Функция принимает список с резервами и отправляет сообщение
     за каждый из элементов, добавляя к ним кнопки."""
    for reservation in reservations:
        #context.user_data['reservation'] = reservation
        await send_message(
            update,
            context,
            reservation.reserve_card(),
            InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD),
            reservation=reservation
            )


async def delete_reserve_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция удаляет запись о брони из БД и выводит подтверждение в чат"""
    update.callback_query.answer()
    #reservation = context.user_data['reservation']
    reservation = Reservation.from_json(update.message.api_kwargs['reservation'])
    delete_reservation(reservation)
    await update.callback_query.edit_message_text(
        text='ОТМЕНЕНА' + '\n' + reservation.reserve_card()
    )
    logger.info('\nЗапись удалена:\n{}'.format(reservation.reserve_card()))
    context.user_data.clear()
    return ConversationHandler.END


async def visited_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция обновляет информацию о приходе гостей в бд и изменяет карточку резерва"""
    update.callback_query.answer()
    reservation = context.user_data['reservation']
    reservation.visited_on_off()
    edit_reservation(reservation)
    await update.callback_query.edit_message_text(
        text=reservation.reserve_card(),
        reply_markup=InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD)
    )
    logger.info('\nИзменился статус визита:\n{}'.format(reservation.reserve_card()))
    return ConversationHandler.END


async def edit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает параметры резерва, которые можно изменить"""
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


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить имя в резерве"""
    await send_message(
        update,
        context,
        'Текущее имя в резерве: ' + context.user_data['reservation'].guest_name + '\n' + 'Отправь мне новое!'
    )
    context.user_data['changed'] = 'name'
    await update.callback_query.answer()


async def edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить время визита в резерве"""
    await send_message(
        update,
        context,
        'Текущее время визита в резерве: ' + str(context.user_data['reservation'].date_time) + '\n' + 'Отправь мне новое!'
    )
    context.user_data['changed'] = 'time'


async def edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция предлагает изменить детали в резерве"""
    await send_message(
        update,
        context,
        'Детали: ' + context.user_data['reservation'].info + '\n' + 'На что меняем?'
    )
    context.user_data['changed'] = 'info'


async def edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет новую информацию и выводит обновленный резерв"""
    changed = context.user_data['changed']
    if changed == 'name':
        context.user_data['reservation'].guest_name = update.message.text
    elif changed == 'time':
        context.user_data['reservation'].date_time = update.message.text
    elif changed == 'info':
        context.user_data['reservation'].info = update.message.text

    reservation = context.user_data['reservation']

    edit_reservation(reservation)

    logger.info('\nБронь изменена:\n{}'.format(reservation.reserve_card()))
    await send_message(update, context, help_texts.RESERVER_ADDITION_END_SAVE)
    await send_message(update,
                       context,
                       reservation.reserve_card(),
                       reply_markup=InlineKeyboardMarkup(RESERVE_CARD_KEYBOARD)
    )
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
        if query.data == 'edit_name':
            await edit_name(update, context)
            return EDIT_NAME
        if query.data == 'edit_datetime':
            await edit_time(update, context)
            return EDIT_DATETIME
        if query.data == 'edit_info':
            await edit_info(update, context)
            return EDIT_INFO
    except KeyError as err:
        logger.info(f'!!!!!!!!!!!!!OSHIBKA:{err}')
        await send_message(update, context, help_texts.CARD_BUTTONS_ERROR_MSG)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    await send_message(update, context, help_texts.GREETINGS)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    await send_message(update, context, help_texts.HELP)


async def allreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /allreserves. Выводит резервы за ВСЁ время. ДЛЯ ДЕБАГУ"""
    await reservations_to_messages(update, context, show_reservations_all())


async def todayreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /todayreserves. Выводит резервы на текущий день"""
    await reservations_to_messages(update, context, show_reservations_today())


async def addreserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог о записи резерва и спрашивает имя гостя"""
    context.user_data['reservation'] = Reservation()
    await send_message(update, context, help_texts.RESERVER_ADDITION_START)
    await send_message(
        update, context, help_texts.RESERVER_ADDITION_GUEST_NAME
    )
    return GUEST_NAME


async def guest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает имя гостя и запрашивает дату и время визита"""
    context.user_data['reservation'].guest_name = update.message.text
    await send_message( update, context, help_texts.RESERVER_ADDITION_TIME)
    return DATE_TIME


async def date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дату и время визита и запрашивает дополнительную информацию"""
    context.user_data['reservation'].date_time = update.message.text
    await send_message(update, context, help_texts.RESERVER_ADDITION_MORE_INFO)
    return MORE_INFO


async def more_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дополнительную информацию.
    Выводит собраную информацию о брони с возможностью подтвердить / отменить запись"""
    context.user_data['reservation'].info = update.message.text
    reply_keyboard = [['Сохранить', 'Отмена']]

    await send_message(update, context, help_texts.RESERVER_ADDITION_SAVE_EDIT_DELETE)
    await send_message(
        update, context,
        context.user_data['reservation'].reserve_preview(),
        ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Шо делаем?'
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
    context.user_data['reservation'].user_added = update.effective_user.name
    reservation = context.user_data['reservation']
    add_reservation(reservation)
    logger.info('\nБронь сохранена:\n{}'.format(reservation.reserve_card()))
    await send_message(update, context, help_texts.RESERVER_ADDITION_END_SAVE)
    await send_message(update, context, await reservations_to_messages(update, context, [reservation,]))
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработку команды /start
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Добавляем обработку команды /help
    help_handler = CommandHandler('help', help_command)
    application.add_handler(help_handler)

    # Добавляем обработку команды /allreserves
    allreserves_handler = CommandHandler('allreserves', allreserves)
    application.add_handler(allreserves_handler)

    # Добавляем обработку команды /todayreserves
    todayreserves_handler = CommandHandler('todayreserves', todayreserves)
    application.add_handler(todayreserves_handler)

    # Добавляем обработку команды /addreserve
    addreserve_handler = ConversationHandler(
        entry_points=[CommandHandler('addreserve', addreserve)],
        states={
            GUEST_NAME: [MessageHandler(filters.TEXT, guest_name)],
            DATE_TIME: [MessageHandler(filters.TEXT, date_time)],
            MORE_INFO: [MessageHandler(filters.TEXT, more_info)],
            CHOICE: [
                MessageHandler(filters.Regex('^Сохранить$'), end_save),
                MessageHandler(filters.Regex('^Отмена$'), cancel_new_reserve),
            ],
        },
        fallbacks=(),
    )

    application.add_handler(addreserve_handler)

    # Добавляем обработку запроса на редактирование резерва
    editreserve_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button),
        ],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT, edit_save)],
            EDIT_DATETIME: [MessageHandler(filters.TEXT, edit_save)],
            EDIT_INFO: [MessageHandler(filters.TEXT, edit_save)],
        },
        fallbacks=(),
    )

    application.add_handler(editreserve_handler)

    # Поллинг
    application.run_polling()


if __name__ == '__main__':
    main()
