import os
import logging

from dotenv.main import load_dotenv
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler,
)

import help_texts

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


#временный словарь под данные резерва для дебага
RESERVE_DICT = {
    'name': '',
    'time': '',
    'more_info': '',
    'who_added': '',
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_texts.GREETINGS
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_texts.HELP
    )


async def addreserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог о записи резерва и спрашивает имя гостя"""
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_START + help_texts.RESERVER_ADDITION_GUEST_NAME,
        reply_markup=ReplyKeyboardRemove()
    )
    return GUEST_NAME


async def guest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает имя гостя и запрашивает дату и время визита"""
    RESERVE_DICT['name'] = update.message.text
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_TIME,
        reply_markup=ReplyKeyboardRemove()
    )
    return DATE_TIME


async def date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дату и время визита и запрашивает дополнительную информацию"""
    RESERVE_DICT['time'] = update.message.text
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_MORE_INFO,
        reply_markup=ReplyKeyboardRemove()
    )
    return MORE_INFO


async def more_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Записывает дополнительную информацию.
    Выводит собраную информацию о брони с возможностью подтвердить / изменить / отменить запись"""
    RESERVE_DICT['more_info'] = update.message.text
    reply_keyboard = [['Сохранить', 'Изменить', 'Отмена']]
    
    await update.message.reply_text(
        help_texts.RESERVER_ADDITION_SAVE_EDIT_DELETE + 'Бронь:',
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        RESERVE_DICT,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Шо делаем?'
        ),
    )

    #здесь(?) должно быть условие на сохранить/изменить/отменить
    return END


async def end_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет запись и заканчивает сбор данных"""
    RESERVE_DICT['who_added'] = update.effective_user.name
    logger.info(f'Бронь сохранена: {RESERVE_DICT}')
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
