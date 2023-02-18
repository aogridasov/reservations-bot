import logging
import os

from typing import List
from dotenv.main import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters, CallbackQueryHandler)

import help_texts
from reservations import (DB_CONNECTION, DB_CURSOR, Reservation,
                          add_reservation, show_reservations_all,
                          show_reservations_today)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    exit('No TG token found!')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

GUEST_NAME, DATE_TIME, MORE_INFO, END = range(4)


async def send_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_text,
    reply_markup=ReplyKeyboardRemove()
):
    """Шорткат для отправки сообщения"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg_text,
        reply_markup=reply_markup
    )


async def reservations_to_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reservations: List[Reservation]
) -> None:
    """Функция принимает список с резервами и отправляет сообщение
     за каждый из элементов, добавляя к ним кнопки."""
    keyboard = [
        [InlineKeyboardButton('Гости пришли', callback_data='1')],
        [
            InlineKeyboardButton('Удалить бронь', callback_data='2'),
            InlineKeyboardButton('Изменить бронь', callback_data='3'),
        ],
    ]
    for reservation in reservations:
        await send_message(
            update,
            context,
            reservation.reserve_card(),
            InlineKeyboardMarkup(keyboard)
            )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    await send_message(update, context, help_texts.GREETINGS)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    await send_message(update, context, help_texts.HELP)


async def allreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /allreserves. Выводит резервы за ВСЁ время. ДЛЯ ДЕБАГУ"""
    reservations = show_reservations_all()
    await reservations_to_messages(update, context, reservations)


async def todayreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /todayreserves. Выводит резервы на текущий день"""
    reservations = show_reservations_today()
    await reservations_to_messages(update, context, reservations)


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
    Выводит собраную информацию о брони с возможностью подтвердить / изменить / отменить запись"""
    context.user_data['reservation'].info = update.message.text
    reply_keyboard = [['Сохранить', 'Изменить', 'Отмена']]

    await send_message(update, context, help_texts.RESERVER_ADDITION_SAVE_EDIT_DELETE)
    await send_message(
        update, context,
        context.user_data['reservation'].reserve_preview(),
        ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Шо делаем?'
        )
    )
    return END


async def end_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет запись и заканчивает сбор данных"""
    context.user_data['reservation'].user_added = update.effective_user.name
    add_reservation(context.user_data['reservation'])
    logger.info('Бронь сохранена.')
    await send_message(update, context, help_texts.RESERVER_ADDITION_END_SAVE)
    return ConversationHandler.END


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработку команды /start
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Добавляем обработку команды /help
    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    # Добавляем обработку команды /allreserves
    allreserves_handler = CommandHandler('allreserves', allreserves)
    application.add_handler(allreserves_handler)

    # Добавляем обработку команды /todayreserves
    todayreserves_handler = CommandHandler('todayreserves', todayreserves)
    application.add_handler(todayreserves_handler)

    # Добавляем обработку кнопочек
    application.add_handler(CallbackQueryHandler(button))
 
    # Добавляем обработку команды /addreserve
    addreserve_handler = ConversationHandler(
        entry_points=[CommandHandler('addreserve', addreserve)],
        states={
            GUEST_NAME: [MessageHandler(filters.TEXT, guest_name)],
            DATE_TIME: [MessageHandler(filters.TEXT, date_time)],
            MORE_INFO: [MessageHandler(filters.TEXT, more_info)],
            END: [MessageHandler(filters.TEXT, end_save)],
        },
        fallbacks=(),
    )

    application.add_handler(addreserve_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
