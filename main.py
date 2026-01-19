import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ВСТАВЬ СЮДА СВОЙ ТОКЕН!
TOKEN = "8514308190:AAH8ztsvN_2EYQ4-L8PpAjnsQ0aBZi4rERo"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния
GET_OBJECT, CONFIRM_START, ASK_QUESTIONS = range(3)

# Все вопросы чек-листа с блоками
QUESTIONS = [
    # Блок 1: Оклейка входной двери
    {"block": 1, "text": "Контур двери заклеен двухсторонним скотчем?"},
    {"block": 1, "text": "Полотно оклеено ударопрочным материалом?"},
    {"block": 1, "text": "Снаружи наклеен логотип компании?"},
    {"block": 1, "text": "Внутри размещены правила компании?"},
    {"block": 1, "text": "Установлен временный сейф для хранения ключей?"},
    {"block": 1, "text": "Влажная тряпка на входе?"},
    {"block": 1, "text": "Временный унитаз установлен?"},
    {"block": 1, "text": "Временный доступ к воде?"},
    
    # Блок 2: Окна и подоконники
    {"block": 2, "text": "Окна заклеены плёнкой?"},
    {"block": 2, "text": "Подоконники защищены ударостойким материалом?"},
    {"block": 2, "text": "Радиаторы укрыты полностью и качественно?"},
    
    # Блок 3: Инфраструктура объекта
    {"block": 3, "text": "Есть раздевалка?"},
    {"block": 3, "text": "Аптечка присутствует?"},
    {"block": 3, "text": "Есть бокс/кейc для документов/материалов?"},
    {"block": 3, "text": "В каждой комнате при наличии — размещён лист с дизайн-проектом на стене?"},
    
    # Блок 4: Чистовые материалы
    {"block": 4, "text": "Аккуратно сложены?"},
    {"block": 4, "text": "Укрыты защитным материалом?"},
    
    # Блок 5: Черновые материалы
    {"block": 5, "text": "Сложены в отведённом месте?"},
    {"block": 5, "text": "Находятся в чистом виде, без пыли и грязи?"},
    
    # Блок 6: Бытовой мусор
    {"block": 6, "text": "На объекте нет разбросанного мусора?"},
    
    # Блок 7: Порядок после работ
    {"block": 7, "text": "Наведён порядок после последнего этапа работ?"},
    {"block": 7, "text": "На объекте нет запаха сигарет?"}
]

# Названия блоков
BLOCK_NAMES = {
    1: "1. Оклейка входной двери",
    2: "2. Окна и подоконники", 
    3: "3. Инфраструктура объекта",
    4: "4. Чистовые материалы",
    5: "5. Черновые материалы",
    6: "6. Бытовой мусор",
    7: "7. Порядок после работ"
}

# Кнопки Да/Нет
yes_no_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("Да"), KeyboardButton("Нет")]
], resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context):
    """Начало работы - запрашиваем номер объекта"""
    # Очищаем старые данные
    context.user_data.clear()
    await update.message.reply_text("Привет! Какой номер объекта?")
    return GET_OBJECT

async def get_object_number(update: Update, context):
    """Получаем номер объекта и подтверждаем начало"""
    object_number = update.message.text
    
    # Проверяем, что введен номер (содержит цифры)
    if not any(char.isdigit() for char in object_number):
        await update.message.reply_text("Пожалуйста, введите номер объекта (должен содержать цифры):")
        return GET_OBJECT
    
    context.user_data['object_number'] = object_number
    context.user_data['score'] = 0
    context.user_data['current_question'] = 0
    context.user_data['block_scores'] = {i: 0 for i in range(1, 8)}
    context.user_data['block_totals'] = {i: 0 for i in range(1, 8)}
    
    # Считаем вопросы по блокам
    for question in QUESTIONS:
        block = question["block"]
        context.user_data['block_totals'][block] += 1
    
    await update.message.reply_text(
        f"Объект №{object_number}\n"
        "Проведём аудит объекта по чек-листу чистоты. Отвечай «Да» или «Нет» — начнём?",
        reply_markup=yes_no_keyboard
    )
    return CONFIRM_START

async def confirm_start(update: Update, context):
    """Подтверждение начала аудита"""
    answer = update.message.text
    
    if answer not in ['Да', 'Нет']:
        await update.message.reply_text("Пожалуйста, используйте кнопки Да/Нет")
        return CONFIRM_START
    
    if answer == 'Нет':
        await update.message.reply_text("Аудит отменен. Для начала напишите /start")
        return ConversationHandler.END
    
    # Начинаем аудит - задаем первый вопрос
    await ask_next_question(update, context)
    return ASK_QUESTIONS

async def ask_next_question(update: Update, context):
    """Задаем следующий вопрос с учетом блоков"""
    current = context.user_data['current_question']
    
    if current < len(QUESTIONS):
        question_data = QUESTIONS[current]
        block = question_data["block"]
        question_text = question_data["text"]
        
        # Если это первый вопрос блока - показываем название блока
        if current == 0 or QUESTIONS[current-1]["block"] != block:
            await update.message.reply_text(BLOCK_NAMES[block])
        
        await update.message.reply_text(
            f"{current + 1}. {question_text}",
            reply_markup=yes_no_keyboard
        )
    else:
        # Все вопросы заданы - показываем результат
        await show_results(update, context)
        # ВОТ ГЛАВНОЕ ИСПРАВЛЕНИЕ - возвращаем END напрямую
        return ConversationHandler.END

async def handle_answer(update: Update, context):
    """Обрабатываем ответы на вопросы"""
    answer = update.message.text
    
    if answer not in ['Да', 'Нет']:
        await update.message.reply_text("Пожалуйста, используйте кнопки Да/Нет")
        return ASK_QUESTIONS
    
    # Считаем баллы
    current = context.user_data['current_question']
    block = QUESTIONS[current]["block"]
    
    if answer == 'Да':
        context.user_data['score'] += 1
        context.user_data['block_scores'][block] += 1
    
    # Переходим к следующему вопросу
    context.user_data['current_question'] += 1
    
    # Задаем следующий вопрос
    await ask_next_question(update, context)
    
    # Возвращаем состояние, которое вернула ask_next_question
    if context.user_data['current_question'] >= len(QUESTIONS):
        return ConversationHandler.END
    return ASK_QUESTIONS

async def show_results(update: Update, context):
    """Показываем итоговый результат"""
    score = context.user_data['score']
    total = len(QUESTIONS)
    object_number = context.user_data['object_number']
    block_scores = context.user_data['block_scores']
    block_totals = context.user_data['block_totals']
    
    # Определяем оценку
    if score >= 20:
        rating = "Отлично"
        recommendation = "Отличная работа! Поддерживайте текущий уровень чистоты."
    elif score >= 16:
        rating = "Хорошо"
        recommendation = "Рекомендую устранить мелкие замечания до следующей проверки."
    elif score >= 14:
        rating = "Удовлетворительно"
        recommendation = "Требуется внимание к некоторым аспектам чистоты."
    else:
        rating = "Требуется немедленное исправление"
        recommendation = "Срочно примите меры по улучшению чистоты на объекте!"
    
    # Формируем детализацию по блокам
    block_details = []
    for block_num in range(1, 8):
        block_name = BLOCK_NAMES[block_num]
        block_score = block_scores[block_num]
        block_total = block_totals[block_num]
        block_details.append(f"{block_name}: {block_score}/{block_total}")
    
    result_text = f"""📊 Результат аудита объекта №{object_number}

• Всего баллов: {score} из {total}
• Оценка: {rating}
• Рекомендация: {recommendation}

Детализация по блокам:
{chr(10).join(block_details)}

Для нового аудита напишите /start"""
    
    await update.message.reply_text(result_text, reply_markup=None)

async def cancel(update: Update, context):
    """Отмена аудита"""
    await update.message.reply_text(
        "Аудит отменен. Для нового аудита напишите /start",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_OBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_object_number)],
            CONFIRM_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_start)],
            ASK_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    print("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
