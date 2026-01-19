import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask для Health Checks
server = Flask(__name__)

@server.route('/')
def home():
    return "Audit Bot is running", 200

@server.route('/health')
def health():
    return {"status": "healthy"}, 200

# Переменные для Telegram
TOKEN = os.getenv("TOKEN")
GET_OBJECT, CONFIRM_START, ASK_QUESTIONS = range(3)

# Данные чек-листа
QUESTIONS = [
    {"block": 1, "text": "Контур двери заклеен двухсторонним скотчем?"},
    {"block": 1, "text": "Полотно оклеено ударопрочным материалом?"},
    {"block": 1, "text": "Снаружи наклеен логотип компании?"},
    {"block": 1, "text": "Внутри размещены правила компании?"},
    {"block": 1, "text": "Установлен временный сейф для хранения ключей?"},
    {"block": 1, "text": "Влажная тряпка на входе?"},
    {"block": 1, "text": "Временный унитаз установлен?"},
    {"block": 1, "text": "Временный доступ к воде?"},
    {"block": 2, "text": "Окна заклеены плёнкой?"},
    {"block": 2, "text": "Подоконники защищены ударостойким материалом?"},
    {"block": 2, "text": "Радиаторы укрыты полностью и качественно?"},
    {"block": 3, "text": "Есть раздевалка?"},
    {"block": 3, "text": "Аптечка присутствует?"},
    {"block": 3, "text": "Есть бокс/кейc для документов/материалов?"},
    {"block": 3, "text": "В каждой комнате при наличии — размещён лист с дизайн-проектом на стене?"},
    {"block": 4, "text": "Аккуратно сложены?"},
    {"block": 4, "text": "Укрыты защитным материалом?"},
    {"block": 5, "text": "Сложены в отведённом месте?"},
    {"block": 5, "text": "Находятся в чистом виде, без пыли и грязи?"},
    {"block": 6, "text": "На объекте нет разбросанного мусора?"},
    {"block": 7, "text": "Наведён порядок после последнего этапа работ?"},
    {"block": 7, "text": "На объекте нет запаха сигарет?"}
]

BLOCK_NAMES = {
    1: "1. Оклейка входной двери",
    2: "2. Окна и подоконники", 
    3: "3. Инфраструктура объекта",
    4: "4. Чистовые материалы",
    5: "5. Черновые материалы",
    6: "6. Бытовой мусор",
    7: "7. Порядок после работ"
}

yes_no_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("Да"), KeyboardButton("Нет")]
], resize_keyboard=True, one_time_keyboard=True)

# --- Логика бота (Функции) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Привет! Какой номер объекта?")
    return GET_OBJECT

async def get_object_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    object_number = update.message.text
    if not any(char.isdigit() for char in object_number):
        await update.message.reply_text("Введите номер объекта (цифрами):")
        return GET_OBJECT
    
    context.user_data['object_number'] = object_number
    context.user_data['score'] = 0
    context.user_data['current_question'] = 0
    context.user_data['block_scores'] = {i: 0 for i in range(1, 8)}
    context.user_data['block_totals'] = {i: 0 for i in range(1, 8)}
    
    for question in QUESTIONS:
        context.user_data['block_totals'][question["block"]] += 1
    
    await update.message.reply_text(
        f"Объект №{object_number}\nНачнем аудит?",
        reply_markup=yes_no_keyboard
    )
    return CONFIRM_START

async def confirm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'Да':
        await ask_next_question(update, context)
        return ASK_QUESTIONS
    await update.message.reply_text("Отменено. /start для начала.")
    return ConversationHandler.END

async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data['current_question']
    if current < len(QUESTIONS):
        q = QUESTIONS[current]
        if current == 0 or QUESTIONS[current-1]["block"] != q["block"]:
            await update.message.reply_text(f"📝 {BLOCK_NAMES[q['block']]}")
        await update.message.reply_text(f"{current + 1}. {q['text']}", reply_markup=yes_no_keyboard)
    else:
        await show_results(update, context)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.message.text
    if ans not in ['Да', 'Нет']:
        return ASK_QUESTIONS
    
    curr = context.user_data['current_question']
    if ans == 'Да':
        context.user_data['score'] += 1
        context.user_data['block_scores'][QUESTIONS[curr]["block"]] += 1
    
    context.user_data['current_question'] += 1
    if context.user_data['current_question'] < len(QUESTIONS):
        await ask_next_question(update, context)
        return ASK_QUESTIONS
    
    await show_results(update, context)
    return ConversationHandler.END

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = context.user_data['score']
    details = [f"{BLOCK_NAMES[i]}: {context.user_data['block_scores'][i]}/{context.user_data['block_totals'][i]}" for i in range(1, 8)]
    
    res = f"📊 Объект №{context.user_data['object_number']}\nБаллов: {score}/{len(QUESTIONS)}\n\n" + "\n".join(details)
    await update.message.reply_text(res, reply_markup=None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Аудит прерван.")
    return ConversationHandler.END

# --- Запуск серверов ---

def run_flask():
    port = int(os.environ.get("PORT", 3000))
    server.run(host='0.0.0.0', port=port)

def main():
    # 1. Запуск Flask в фоне
    Thread(target=run_flask, daemon=True).start()

    # 2. Запуск Бота
    application = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_OBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_object_number)],
            CONFIRM_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_start)],
            ASK_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv)
    print("Бот и Flask запущены...")
    application.run_polling()

if __name__ == '__main__':
    main()
