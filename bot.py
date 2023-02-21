import logging
import os
from typing import List

from dotenv.main import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)

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
        [InlineKeyboardButton('Гости пришли', callback_data='visited')],
        [
            InlineKeyboardButton('Удалить бронь', callback_data='delete_reservation'),
            InlineKeyboardButton('Изменить бронь', callback_data='edit_reservation'),
        ],
    ]
    for reservation in reservations:
        context.user_data['reservation_instance'] = reservation
        await send_message(
            update,
            context,
            reservation.reserve_card(),
            InlineKeyboardMarkup(keyboard)
            )


async def editreserve(update: Update, context: ContextTypes.DEFAULT_TYPE)
    """Выводит информацию о резерве в поле ввода и позволяет сохранить изменения"""
    #context.user_data['reservation'] = Reservation()
    #await send_message(update, context, help_texts.RESERVER_ADDITION_START)
    #await send_message(
    #    update, context, help_texts.RESERVER_ADDITION_GUEST_NAME
    #)
    #return GUEST_NAME
    pass

async def edit_reserve_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция инициирует диалог для изменения данных о брони"""
    await send_message(update, context, 'cant edit yet')


async def delete_reserve_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция удаляет запись о брони из БД и выводит подтверждение в чат"""
    reservation = context.user_data['reservation_instance']
    delete_reservation(reservation)
    await update.callback_query.edit_message_text(
        text='ОТМЕНЕНА' + '\n' + reservation.reserve_card()
    )
    logger.info('\nЗапись удалена:\n{}'.format(reservation.reserve_card()))


async def visited_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Функция обновляет информацию о приходе гостей в бд и изменяет карточку резерва"""
    reservation = context.user_data['reservation_instance']
    reservation.visited_on_off()
    edit_reservation(reservation)
    await update.callback_query.edit_message_text(text=reservation.reserve_card())
    logger.info('\nИзменился статус визита:\n{}'.format(reservation.reserve_card()))


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает выбор кнопки в карточке резерва"""
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    try:
        if query.data == 'delete_reservation':
            await delete_reserve_button(update, context)
        elif query.data == 'edit_reservation':
            await edit_reserve_button(update, context)
        elif query.data == 'visited':
            await visited_button(update, context)
    except KeyError:
        await send_message(update, context, help_texts.CARD_BUTTONS_ERROR_MSG)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    await send_message(update, context, help_texts.GREETINGS)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    reservation = context.user_data['reservation']
    add_reservation(reservation)
    logger.info('\nБронь сохранена:\n{}'.format(reservation.reserve_card()))
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
