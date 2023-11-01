import calendar, time, os, logging, schedule, threading
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (CommandHandler, Updater, MessageHandler, Filters,
                           CallbackQueryHandler, ConversationHandler)
from dotenv import load_dotenv

from money_box.wsgi import * #Это для того, чтобы импортировать модели из Джанго
from django.db.models import Sum
from app.models import Payments, Category

load_dotenv()

token = os.getenv('TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

CONFIRM, EDIT, EDIT_DATE, EDIT_AMOUNT, EDIT_DESCRIPTION, EDIT_CATEGORY, SEE_DATE = range(7)
TARGET = 200000
user_data = {}

# Пробуждение. Команда "/start"
def wake_up(update, context):
    chat = update.effective_chat
    name = update.message.chat.first_name
    buttons = ReplyKeyboardMarkup(
        [['/costs', '/result'], ['/categories', '/costsdate']], resize_keyboard=True)
    context.bot.send_message(
        chat_id=chat.id,
        text=('Привет, {}. Здесь можно добавить свои расходы и узнать, сколько уже потрачено за месяц. Напиши ниже, что и почем куплено, например так: "582 хлебник".').format(name),
        reply_markup=buttons
    )
    schedule.every().day.at('10:00').do(send_daily_message, update, context)


# Отправка ежедневного сообщения с напоминанием внести траты.
def send_daily_message(update, context):
    chat = update.effective_chat
    message = 'Проверьте расходы за предыдущий день. Добавьте, если чего-то не хватает.'
    context.bot.send_message(chat_id=chat.id, text=message)
    get_costs_date(update, context, date=None)


# Обработка входящего сообщения с новым расходом "500 Хлебник"
def add_cost(update, context):
    chat = update.effective_chat
    user_id = update.effective_user.id
    text = update.message.text
    amount, description = text.split()
    current_date = datetime.now().strftime("%d.%m.%Y")
    category = Payments.objects.filter(description__iregex=description)
    category = category.first().category if category else Category.objects.get(id=1)
    user_data[user_id] = {'date': current_date,
                          'amount': int(amount),
                          'description': description,
                          'category': category}
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('Подтвердить', callback_data='confirm')],
        [InlineKeyboardButton('Изменить', callback_data='edit')]])
    context.bot.send_message(
        chat_id=chat.id,
        text=('Дата - {}\nСумма - {}\nОписание - {}\nКатегория - {}').format(current_date, amount, description, category.title),
        reply_markup=buttons)
    return CONFIRM


# Обработка нажатия кнопки подтверждения после ввода расхода.
def confirm(update, context):
    chat = update.effective_chat
    user_id = update.effective_user.id
    date_str = user_data[user_id]['date']
    date_format = '%d.%m.%Y'
    date = datetime.strptime(date_str, date_format)
    payment = Payments.objects.create(
        date=date,
        amount=user_data[user_id]['amount'],
        description=user_data[user_id]['description'],
        category=user_data[user_id]['category']
        )
    payment.save()
    update.callback_query.answer("Данные сохранены.")
    del user_data[user_id]
    costs, reserve = calculate_costs()
    if reserve > 0:
        context.bot.send_message(
            chat_id=chat.id,
            text=('✅✅✅Расход успешно добавлен!\nВ этом месяце потрачено {} руб.\nРезерв {} руб.').format(costs, reserve)
            )
    else:
        context.bot.send_message(
            chat_id=chat.id,
            text=('⚠️⚠️⚠️Расход успешно добавлен!\nВ этом месяце потрачено {} руб.\nПерелимит {} руб.').format(costs, reserve)
            )
    return ConversationHandler.END


# Обработка нажатия кнопки изменения расхода после его ввода.
def edit(update, context):
    chat = update.effective_chat
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('Дату', callback_data='edit_date'),
         InlineKeyboardButton('Сумму', callback_data='edit_amount')],
         [InlineKeyboardButton('Описание', callback_data='edit_description'),
          InlineKeyboardButton('Категорию', callback_data='edit_category')]
          ])
    context.bot.send_message(
        chat_id=chat.id,
        text=('Выберете, что изменить:'),
        reply_markup=buttons
    )
    return EDIT


def edit_date(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=('Введите новую дату в формате "23.10" или "23.10.2023"')
        )
    return EDIT_DATE


def edit_amount(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=('Введите новую сумму в формате целого числа "500"')
        )
    return EDIT_AMOUNT


def edit_description(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=('Введите новое описание')
        )
    return EDIT_DESCRIPTION


def edit_category(update, context):
    chat = update.effective_chat
    categories = Category.objects.all()
    categories = [category.title for category in categories]
    buttons = [InlineKeyboardButton(category, callback_data=f"category_{i+1}") for i, category in enumerate(categories)]
    button_rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    reply_markup = InlineKeyboardMarkup(button_rows)
    context.bot.send_message(
        chat_id=chat.id,
        text=('Выберите категорию:'),
        reply_markup=reply_markup)
    return EDIT_CATEGORY


# Обработка изменения значения (даты, суммы, описания и категории)
def edit_value_save(update, context, value_type, new_value):
    chat = update.effective_chat
    user_id = update.effective_user.id
    user_data[user_id][value_type] = new_value
    if value_type == 'description':
        category = Payments.objects.filter(description__iregex=user_data[user_id]['description'])
        user_data[user_id]['category'] = category.first().category if category else Category.objects.first()
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('Подтвердить', callback_data='confirm')],
        [InlineKeyboardButton('Изменить', callback_data='edit')]
    ])
    context.bot.send_message(
        chat_id=chat.id,
        text=('Дата - {}\nСумма - {}\nОписание - {}\nКатегория - {}').format(
            user_data[user_id]['date'],
            user_data[user_id]['amount'],
            user_data[user_id]['description'],
            user_data[user_id]['category'].title),
        reply_markup=buttons)
    return CONFIRM


# Обработка введенной даты(изменение даты)
def edit_date_save(update, context):
    text = update.message.text
    if len(text) < 10:
        current_year = str(datetime.now().year)
        text += '.' + current_year
    edit_value_save(update, context, 'date', text)
    return CONFIRM


# Обработка введенной суммы (изменение суммы)
def edit_amount_save(update, context):
    text = update.message.text
    edit_value_save(update, context, 'amount', int(text))
    return CONFIRM


# Обработка введенного описания (изменение описания)
def edit_description_save(update, context):
    text = update.message.text
    edit_value_save(update, context, 'description', text)
    return CONFIRM


# Обработка выбранной кнопки категории (изменение категории)
def edit_category_save(update, context):
    chat = update.effective_chat
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    category_index = int(data.split("_")[1]) - 1
    selected_category = Category.objects.all()[category_index]
    user_data[user_id]['category'] = selected_category
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('Подтвердить', callback_data='confirm')],
        [InlineKeyboardButton('Изменить', callback_data='edit')]
    ])
    context.bot.send_message(
        chat_id=chat.id,
        text=('Дата - {}\nСумма - {}\nОписание - {}\nКатегория - {}').format(
            user_data[user_id]['date'],
            user_data[user_id]['amount'],
            user_data[user_id]['description'],
            user_data[user_id]['category'].title),
        reply_markup=buttons)
    return CONFIRM


# Вывод списка расходов текущего месяца по команде /get_costs
def get_costs(update, context):
    chat = update.effective_chat
    current_date = datetime.now()
    start_date = datetime(current_date.year, current_date.month, 1)
    result = []
    queryset = Payments.objects.filter(date__gte=start_date, date__lte=current_date)
    for payment in queryset:
        result.append(f'📍{payment.date.strftime("%d.%m")} - {int(payment.amount)} - {payment.description} - {payment.category.title}')
    message_text = '\n'.join(result)
    context.bot.send_message(
        chat_id=chat.id,
        text=message_text)


def know_date(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=('Введите новую дату в формате "23.10" или "23.10.2023"')
        )
    return SEE_DATE


# Обработка введенной даты(посмотреть расходы за дату)
def check_date(update, context):
    text = update.message.text
    if len(text) < 10:
        current_year = str(datetime.now().year)
        text += '.' + current_year
    get_costs_date(update, context, text)
    return ConversationHandler.END


# Вывод списка расходов за определенный день (базовая функция)
def get_costs_date(update, context, date):
    chat = update.effective_chat
    if not date:
        target_date = datetime.now().date() - timedelta(days=1)
    else:
        target_date = date
    date_format = '%d.%m.%Y'
    target_date = datetime.strptime(target_date, date_format).date()
    result = []
    queryset = Payments.objects.filter(date=target_date)
    for payment in queryset:
        result.append(f'📍{payment.date.strftime("%d.%m")} - {int(payment.amount)} - {payment.description} - {payment.category.title}')
    message_text = '\n'.join(result)
    context.bot.send_message(
        chat_id=chat.id,
        text=message_text)


# Вывод результатов текущего месяца по категориям по команде /categories
def get_categories(update, context):
    chat = update.effective_chat
    current_date = datetime.now()
    start_date = datetime(current_date.year, current_date.month, 1)
    categories = Category.objects.all()
    result = []
    queryset = Payments.objects.filter(date__gte=start_date, date__lte=current_date)
    costs = queryset.aggregate(sum=Sum('amount'))
    for category in categories:
        category_costs =  queryset.filter(category=category).aggregate(sum=Sum('amount'))
        costs_sum = category_costs['sum'] if category_costs['sum'] is not None else 0
        result.append(f'📍{category.title} - {costs_sum}')
    message_text = '\n'.join(result)
    context.bot.send_message(
        chat_id=chat.id,
        text=('Потрачено итого - {}\n{}').format(costs['sum'], message_text))


# Вывод результатов текущего месяца по команде /result
def get_result(update, context):
    chat = update.effective_chat
    costs, reserve = calculate_costs()
    if reserve > 0:
        context.bot.send_message(
            chat_id=chat.id,
            text=('В этом месяце потрачено {} руб.\n✅✅✅Резерв {} руб.').format(costs, reserve)
            )
    else:
        context.bot.send_message(
            chat_id=chat.id,
            text=('В этом месяце потрачено {} руб.\n⚠️⚠️⚠️Перелимит {} руб.').format(costs, reserve)
            )


# Расчет суммы расходов за месяц и текущего резерва/перелимита
def calculate_costs():
    current_date = datetime.now()
    start_date = datetime(current_date.year, current_date.month, 1)
    costs = Payments.objects.filter(date__gte=start_date, date__lte=current_date).aggregate(
        sum=Sum('amount'))
    costs_sum = costs['sum']

    _, last_day = calendar.monthrange(current_date.year, current_date.month)
    end_date = datetime(current_date.year, current_date.month, last_day)
    days_in_month = (end_date - start_date + timedelta(days=1)).days
    days_passed = (current_date - start_date + timedelta(days=1)).days
    reserve = int((TARGET * days_passed / days_in_month - float(costs_sum)))
    return costs_sum, reserve


# Функция для создания параллельного потока для отправки ежедневных сообщений
def schedule_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    updater = Updater(token=token)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(CommandHandler('categories', get_categories))
    updater.dispatcher.add_handler(CommandHandler('costs', get_costs))
    updater.dispatcher.add_handler(CommandHandler('result', get_result))

    conversation_handler_1 = ConversationHandler(
    entry_points=[(CommandHandler('costsdate', know_date))],
    states={
        SEE_DATE: [MessageHandler(Filters.text, check_date)]},
    fallbacks=[],
    )
    updater.dispatcher.add_handler(conversation_handler_1)


    conversation_handler_2 = ConversationHandler(
        entry_points=[(MessageHandler(Filters.regex(r'^\d+\s[A-Za-z0-9]+$'), add_cost))],
        states={
            CONFIRM: [CallbackQueryHandler(confirm, pattern='confirm'),
                      CallbackQueryHandler(edit, pattern='edit')],
            EDIT: [CallbackQueryHandler(edit_date, pattern='edit_date'),
                   CallbackQueryHandler(edit_amount, pattern='edit_amount'),
                   CallbackQueryHandler(edit_description, pattern='edit_description'),
                   CallbackQueryHandler(edit_category, pattern='edit_category')],
            EDIT_DATE: [MessageHandler(Filters.text, edit_date_save)],
            EDIT_AMOUNT: [MessageHandler(Filters.text, edit_amount_save)],
            EDIT_DESCRIPTION: [MessageHandler(Filters.text, edit_description_save)],
            EDIT_CATEGORY: [CallbackQueryHandler(edit_category_save)]
        },
        fallbacks=[],
    )
    updater.dispatcher.add_handler(conversation_handler_2)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    schedule_thread = threading.Thread(target=schedule_loop)
    schedule_thread.start()
    main()
