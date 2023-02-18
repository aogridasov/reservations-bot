import logging
import os

from dotenv.main import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

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
    reply_markup=None
):
    """Шорткат для отправки сообщения"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg_text,
        reply_markup=reply_markup
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    await send_message(update, context, help_texts.GREETINGS)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    await send_message(update, context, help_texts.HELP)


async def allreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /allreserves. Выводит резервы за ВСЁ время. ДЛЯ ДЕБАГУ"""
    reservations = show_reservations_all()
    for reservation in reservations:
        await send_message(update, context, reservation.reserve_card())


async def todayreserves(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /todayreserves. Выводит резервы на текущий день"""
    reservations = show_reservations_today()
    for reservation in reservations:
        await send_message(update, context, reservation.reserve_card())


async def addreserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог о записи резерва и спрашивает имя гостя"""
    context.user_data['reservation'] = Reservation()
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_START + help_texts.RESERVER_ADDITION_GUEST_NAME,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_START + help_texts.RESERVER_ADDITION_GUEST_NAME,
        reply_markup=ReplyKeyboardRemove()
    )
    return GUEST_NAME


async def guest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает имя гостя и запрашивает дату и время визита"""
    context.user_data['reservation'].guest_name = update.message.text
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_TIME,
        reply_markup=ReplyKeyboardRemove()
    )
    return DATE_TIME


async def date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дату и время визита и запрашивает дополнительную информацию"""
    context.user_data['reservation'].date_time = update.message.text
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_MORE_INFO,
        reply_markup=ReplyKeyboardRemove()
    )
    return MORE_INFO


async def more_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дополнительную информацию.
    Выводит собраную информацию о брони с возможностью подтвердить / изменить / отменить запись"""
    context.user_data['reservation'].info = update.message.text
    reply_keyboard = [['Сохранить', 'Изменить', 'Отмена']]

    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_SAVE_EDIT_DELETE,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        context.user_data['reservation'].reserve_preview(),
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Шо делаем?'
        ),
    )
    return END


async def end_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет запись и заканчивает сбор данных"""
    context.user_data['reservation'].user_added = update.effective_user.name
    add_reservation(context.user_data['reservation'])
    logger.info('Бронь сохранена.')
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_END_SAVE,
        reply_markup=ReplyKeyboardRemove()
    )
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
