import logging
import os
import json
import datetime
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Для Render - добавляем Flask для поддержания активности
from flask import Flask
from threading import Thread

# Состояния диалога
(RATING, INTUITIVE, SLOW_ACTION, CRITICAL_FEATURES, COMPETITORS, IMPROVEMENTS, WISHES, VIDEO) = range(8)

# Включим логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения Render
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Нет токена! Добавьте BOT_TOKEN в переменные окружения Render")

# Ссылка на ваш сайт/приложение
SITE_URL = os.environ.get('SITE_URL', 'https://admin-smudge-10931819.figma.site/')

# ID администраторов (замените на ваш ID)
ADMIN_IDS = [5227791450, 1335650416]  # Ваш ID

# Создаем папки для хранения файлов
if not os.path.exists('videos'):
    os.makedirs('videos')
if not os.path.exists('feedbacks'):
    os.makedirs('feedbacks')

# ------------------------------------------------------------
# Flask сервер для поддержания активности на Render
# ------------------------------------------------------------
app = Flask(__name__)


@app.route('/')
def home():
    return "🤖 Бот для сбора отзывов работает!"


@app.route('/health')
def health():
    return "OK", 200


def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    logger.info(f"🌐 Flask сервер запущен на порту {os.environ.get('PORT', 10000)}")


# ------------------------------------------------------------
# Функции бота
# ------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение со ссылкой на сайт"""
    user = update.effective_user
    welcome_message = f"""
👋 Привет, {user.first_name}!

Я помогу собрать обратную связь о нашем мобильном приложении.

🌐 Сайт приложения: {SITE_URL}

Мы хотим сделать приложение максимально удобным, поэтому зададим несколько важных вопросов о вашем опыте использования.
"""
    await update.message.reply_text(welcome_message)

    # Запрашиваем оценку
    rating_keyboard = [
        [KeyboardButton("⭐ 1"), KeyboardButton("⭐⭐ 2")],
        [KeyboardButton("⭐⭐⭐ 3"), KeyboardButton("⭐⭐⭐⭐ 4")],
        [KeyboardButton("⭐⭐⭐⭐⭐ 5")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        rating_keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "📱 Оцените работу нашего мобильного приложения от 1 до 5:",
        reply_markup=reply_markup
    )
    return RATING


async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем оценку"""
    rating_text = update.message.text
    context.user_data['rating'] = rating_text

    await update.message.reply_text(
        f"Спасибо за оценку: {rating_text}\n\n"
        "🔄 **Насколько интуитивно понятен процесс?**\n"
        "Где вы задумались дольше всего?\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    return INTUITIVE


async def intuitive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ответ о интуитивности"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['intuitive'] = text

    await update.message.reply_text(
        "⏱️ **Какое действие вам показалось самым долгим по количеству нажатий?**\n"
        "Например, чтобы сменить сезон у куртки нужно сделать 5 тапов — это много.\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        parse_mode='Markdown'
    )
    return SLOW_ACTION


async def slow_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ответ о долгих действиях"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['slow_action'] = text

    await update.message.reply_text(
        "🎯 **Что, по вашему мнению, является критической функцией**\n"
        "(без чего нельзя выпускать приложение), а что можно отложить?\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        parse_mode='Markdown'
    )
    return CRITICAL_FEATURES


async def critical_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ответ о критических функциях"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['critical_features'] = text

    await update.message.reply_text(
        "🔍 **Если вы пользовались похожими приложениями,**\n"
        "чего не хватает в этом прототипе по сравнению с ними? Или что лишнее?\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        parse_mode='Markdown'
    )
    return COMPETITORS


async def competitors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ответ о конкурентах"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['competitors'] = text

    await update.message.reply_text(
        "💡 **Что бы вы хотели улучшить в приложении?**\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        parse_mode='Markdown'
    )
    return IMPROVEMENTS


async def improvements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем предложения по улучшению"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['improvements'] = text

    await update.message.reply_text(
        "✨ **Какие функции или возможности вы бы хотели видеть в будущем?**\n"
        "(Напишите ваш ответ или отправьте '-' чтобы пропустить)",
        parse_mode='Markdown'
    )
    return WISHES


async def wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем пожелания"""
    text = update.message.text
    if text == '-':
        text = 'Пропущено'
    context.user_data['wishes'] = text

    await update.message.reply_text(
        "📹 **Запись экрана (необязательно)**\n\n"
        "Вы можете отправить видео использования приложения, чтобы мы лучше поняли ваш опыт.\n"
        "Это поможет нам увидеть проблемные места своими глазами.\n\n"
        "• Отправьте видео (MP4, MOV или AVI)\n"
        "• Или отправьте '-' чтобы пропустить\n\n"
        "*Видео поможет нам сделать приложение еще лучше!*",
        parse_mode='Markdown'
    )
    return VIDEO


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем видео от пользователя"""
    user = update.effective_user

    if update.message.text and update.message.text == '-':
        context.user_data['video'] = 'Пропущено'
        return await finish_feedback(update, context)

    video = update.message.video
    if video:
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"videos/user_{user.id}_{timestamp}.mp4"

            file = await context.bot.get_file(video.file_id)
            await file.download_to_drive(filename)

            video_info = {
                'file_id': video.file_id,
                'file_name': filename,
                'file_size': video.file_size,
                'duration': video.duration,
                'width': video.width,
                'height': video.height,
                'timestamp': timestamp
            }
            context.user_data['video'] = video_info

            await update.message.reply_text(
                "✅ Спасибо! Видео успешно сохранено.\n"
                "Это очень поможет нам в улучшении приложения!"
            )

        except Exception as e:
            logger.error(f"Ошибка при скачивании видео: {e}")
            context.user_data['video'] = 'Ошибка загрузки'
            await update.message.reply_text(
                "❌ Не удалось загрузить видео. Попробуйте еще раз или отправьте '-' чтобы пропустить."
            )
            return VIDEO
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте видео файлом или отправьте '-' чтобы пропустить."
        )
        return VIDEO

    return await finish_feedback(update, context)


async def finish_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершаем сбор отзывов и сохраняем данные"""
    feedback = context.user_data
    user = update.effective_user

    save_feedback(user.id, user.username, user.first_name, feedback)

    video_status = "✅ Загружено" if isinstance(feedback.get('video'), dict) else "❌ Не загружено"
    if feedback.get('video') == 'Пропущено':
        video_status = "⏭️ Пропущено"

    summary = f"""
📋 **Ваш отзыв принят!**

⭐ Оценка: {feedback.get('rating', 'Не указано')}

🔄 Интуитивность: {feedback.get('intuitive', 'Пропущено')[:100]}{'...' if len(feedback.get('intuitive', '')) > 100 else ''}

⏱️ Долгие действия: {feedback.get('slow_action', 'Пропущено')[:100]}{'...' if len(feedback.get('slow_action', '')) > 100 else ''}

🎯 Критические функции: {feedback.get('critical_features', 'Пропущено')[:100]}{'...' if len(feedback.get('critical_features', '')) > 100 else ''}

🔍 Сравнение с аналогами: {feedback.get('competitors', 'Пропущено')[:100]}{'...' if len(feedback.get('competitors', '')) > 100 else ''}

💡 Что улучшить: {feedback.get('improvements', 'Пропущено')[:100]}{'...' if len(feedback.get('improvements', '')) > 100 else ''}

✨ Новые функции: {feedback.get('wishes', 'Пропущено')[:100]}{'...' if len(feedback.get('wishes', '')) > 100 else ''}

📹 Видео: {video_status}

✅ **Большое спасибо за ваш отзыв!** 
Ваше мнение очень важно для нас, мы обязательно учтем все пожелания.
Хорошего дня! 🌟
"""

    await update.message.reply_text(summary, parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END


def save_feedback(user_id, username, first_name, feedback):
    """Сохранение отзыва в файл"""
    feedback_data = {
        'timestamp': str(datetime.datetime.now()),
        'user_id': user_id,
        'username': username or 'Не указан',
        'first_name': first_name,
        'rating': feedback.get('rating', 'Не указано'),
        'intuitive': feedback.get('intuitive', 'Пропущено'),
        'slow_action': feedback.get('slow_action', 'Пропущено'),
        'critical_features': feedback.get('critical_features', 'Пропущено'),
        'competitors': feedback.get('competitors', 'Пропущено'),
        'improvements': feedback.get('improvements', 'Пропущено'),
        'wishes': feedback.get('wishes', 'Пропущено'),
        'video': feedback.get('video', 'Пропущено')
    }

    filename = 'feedbacks/feedbacks.json'

    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
        else:
            feedbacks = []
    except (FileNotFoundError, json.JSONDecodeError):
        feedbacks = []

    feedbacks.append(feedback_data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Сохранен отзыв от пользователя {first_name} (@{username or 'нет'})")


async def all_feedbacks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ВСЕ отзывы пользователей вместе с видео"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    await update.message.reply_text("🔍 Загружаю все отзывы с видео... Это может занять некоторое время.")

    try:
        with open('feedbacks/feedbacks.json', 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)

        if not feedbacks:
            await update.message.reply_text("📭 Пока нет ни одного отзыва.")
            return

        total = len(feedbacks)
        videos_count = count_videos()

        stats = f"""
📊 **ВСЕ ОТЗЫВЫ - ОБЩАЯ СТАТИСТИКА**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 **Всего отзывов:** {total}
🎥 **Всего видео:** {videos_count}
📅 **Период:** {feedbacks[0]['timestamp'][:10]} - {feedbacks[-1]['timestamp'][:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(stats, parse_mode='Markdown')
        await update.message.reply_text("📦 **НАЧАЛО ЗАГРУЗКИ ВСЕХ ОТЗЫВОВ**", parse_mode='Markdown')

        feedbacks.reverse()

        for idx, fb in enumerate(feedbacks, 1):
            feedback_text = format_feedback_message(fb, idx, total)
            video_info = fb.get('video')

            if isinstance(video_info, dict) and 'file_name' in video_info:
                video_path = video_info['file_name']
                if os.path.exists(video_path):
                    try:
                        with open(video_path, 'rb') as video_file:
                            await update.message.reply_video(
                                video=video_file,
                                caption=feedback_text,
                                parse_mode='Markdown',
                                supports_streaming=True
                            )
                    except Exception as e:
                        logger.error(f"Ошибка отправки видео: {e}")
                        await update.message.reply_text(f"{feedback_text}\n\n❌ *Видео недоступно*",
                                                        parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"{feedback_text}\n\n❌ *Видео файл не найден*",
                                                    parse_mode='Markdown')
            else:
                await update.message.reply_text(feedback_text, parse_mode='Markdown')

            await asyncio.sleep(0.5)

        await update.message.reply_text(
            "✅ **ЗАГРУЗКА ЗАВЕРШЕНА**\n\n"
            f"Всего загружено: {total} отзывов\n"
            f"Видео: {videos_count}\n"
            f"Без видео: {total - videos_count}",
            parse_mode='Markdown'
        )

    except FileNotFoundError:
        await update.message.reply_text("📭 Файл с отзывами еще не создан.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке отзывов: {e}")


def format_feedback_message(fb, index, total):
    """Форматирование отзыва для отправки"""
    rating_stars = fb.get('rating', 'Не указано')
    rating_value = rating_stars.count('⭐') if '⭐' in rating_stars else '?'

    text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**ОТЗЫВ #{index} ИЗ {total}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Пользователь:** {fb.get('first_name', 'Неизвестно')}
📱 **Username:** @{fb.get('username', 'нет')}
🆔 **ID:** `{fb.get('user_id', 'Не указан')}`
⏰ **Дата:** {fb.get('timestamp', 'Неизвестно')[:16]}
⭐ **Оценка:** {fb.get('rating', 'Не указано')} ({rating_value}/5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔄 ИНТУИТИВНОСТЬ:**
{fb.get('intuitive', 'Пропущено')}

**⏱️ ДОЛГИЕ ДЕЙСТВИЯ:**
{fb.get('slow_action', 'Пропущено')}

**🎯 КРИТИЧЕСКИЕ ФУНКЦИИ:**
{fb.get('critical_features', 'Пропущено')}

**🔍 СРАВНЕНИЕ С АНАЛОГАМИ:**
{fb.get('competitors', 'Пропущено')}

**💡 ЧТО УЛУЧШИТЬ:**
{fb.get('improvements', 'Пропущено')}

**✨ НОВЫЕ ФУНКЦИИ:**
{fb.get('wishes', 'Пропущено')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return text


async def feedbacks_by_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает отзывы за определенную дату"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Укажите дату в формате ГГГГ-ММ-ДД\n"
                "Пример: `/feedbacks_by_date 2026-02-11`",
                parse_mode='Markdown'
            )
            return

        target_date = args[0]

        with open('feedbacks/feedbacks.json', 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)

        date_feedbacks = [fb for fb in feedbacks if fb['timestamp'][:10] == target_date]

        if not date_feedbacks:
            await update.message.reply_text(f"📭 Нет отзывов за {target_date}")
            return

        await update.message.reply_text(f"📅 **ОТЗЫВЫ ЗА {target_date}** (всего: {len(date_feedbacks)})",
                                        parse_mode='Markdown')

        for idx, fb in enumerate(date_feedbacks, 1):
            text = format_feedback_message(fb, idx, len(date_feedbacks))
            await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def export_feedbacks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт всех отзывов в JSON файл"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    try:
        with open('feedbacks/feedbacks.json', 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'feedbacks/backup_feedbacks_{timestamp}.json'

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, ensure_ascii=False, indent=2)

        with open(backup_file, 'rb') as f:
            await update.message.reply_document(
                document=f,
                caption=f"📊 Экспорт отзывов ({len(feedbacks)} записей)\n📅 {timestamp}"
            )

    except FileNotFoundError:
        await update.message.reply_text("📭 Файл с отзывами не найден.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = """
📱 **Бот для сбора UX-отзывов**

**🔹 Команды для всех:**
/start - Начать опрос
/help - Показать эту справку
/cancel - Отменить текущий опрос
/stats - Показать общую статистику

**🔸 Команды для администратора:**
/all_feedbacks - **ВСЕ ОТЗЫВЫ С ВИДЕО** 🎥
/feedbacks_by_date - Отзывы за дату
/export_feedbacks - Выгрузить в JSON
/admin - Краткий просмотр
/videos - Список видео

**Как отвечать:**
• Отправьте '-' чтобы пропустить вопрос
• Отправьте видео, чтобы поделиться записью экрана

Мы ценим ваше мнение! 🌟
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text(
        "❌ Опрос отменен. Если захотите оставить отзыв, нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def show_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Краткий просмотр последних отзывов"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    try:
        with open('feedbacks/feedbacks.json', 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)

        if not feedbacks:
            await update.message.reply_text("📭 Пока нет ни одного отзыва.")
            return

        total = len(feedbacks)
        ratings = [fb['rating'] for fb in feedbacks if '⭐' in fb['rating']]

        stats = f"""
📊 **КРАТКАЯ СТАТИСТИКА**
━━━━━━━━━━━━━━━━━━
📝 Всего отзывов: {total}
⭐ Средняя оценка: {calculate_average_rating(ratings) if ratings else 'Нет оценок'}
🎥 Всего видео: {count_videos()}
━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(stats, parse_mode='Markdown')
        await update.message.reply_text("📌 **ПОСЛЕДНИЕ 3 ОТЗЫВА:**", parse_mode='Markdown')

        recent_feedbacks = feedbacks[-3:]
        for fb in recent_feedbacks:
            video_status = "✅" if isinstance(fb.get('video'), dict) else "❌"
            text = f"""
👤 **{fb['first_name']}** (@{fb['username']})
⭐ {fb['rating']} {video_status}
📅 {fb['timestamp'][:16]}
💡 {fb['improvements'][:100]}{'...' if len(fb['improvements']) > 100 else ''}
"""
            await update.message.reply_text(text, parse_mode='Markdown')

    except FileNotFoundError:
        await update.message.reply_text("📭 Файл с отзывами еще не создан.")


async def get_videos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для получения списка видео"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    try:
        video_files = []
        for filename in os.listdir('videos'):
            if filename.endswith(('.mp4', '.mov', '.avi')):
                video_files.append(filename)

        if not video_files:
            await update.message.reply_text("📭 Нет загруженных видео.")
            return

        text = f"🎥 **Всего видео:** {len(video_files)}\n\n"
        for i, filename in enumerate(sorted(video_files, reverse=True)[:20], 1):
            text += f"{i}. `{filename}`\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


def count_videos():
    """Подсчет количества видео"""
    try:
        return len([f for f in os.listdir('videos') if f.endswith(('.mp4', '.mov', '.avi'))])
    except:
        return 0


def calculate_average_rating(ratings):
    """Вычисление средней оценки"""
    try:
        numbers = []
        for r in ratings:
            stars = r.count('⭐')
            if stars > 0:
                numbers.append(stars)

        if numbers:
            avg = sum(numbers) / len(numbers)
            return f"{avg:.1f} ⭐ ({len(numbers)} оценок)"
        return "Нет оценок"
    except:
        return "Нет оценок"


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра статистики"""
    try:
        with open('feedbacks/feedbacks.json', 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)

        total = len(feedbacks)
        total_videos = count_videos()

        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for fb in feedbacks:
            stars = fb['rating'].count('⭐')
            if stars in rating_counts:
                rating_counts[stars] += 1

        max_count = max(rating_counts.values()) if rating_counts.values() else 1

        stats_text = f"""
📊 **ОБЩАЯ СТАТИСТИКА**
━━━━━━━━━━━━━━━━━━
👥 Всего отзывов: {total}
🎥 Всего видео: {total_videos}

⭐ **Распределение оценок:**
5 ⭐: {'█' * int((rating_counts[5] / max_count) * 20)} {rating_counts[5]}
4 ⭐: {'█' * int((rating_counts[4] / max_count) * 20)} {rating_counts[4]}
3 ⭐: {'█' * int((rating_counts[3] / max_count) * 20)} {rating_counts[3]}
2 ⭐: {'█' * int((rating_counts[2] / max_count) * 20)} {rating_counts[2]}
1 ⭐: {'█' * int((rating_counts[1] / max_count) * 20)} {rating_counts[1]}

Спасибо, что помогаете нам становиться лучше! 🌟
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    except FileNotFoundError:
        await update.message.reply_text("📭 Пока нет ни одного отзыва. Будьте первым! 🎉")


def main():
    """Запуск бота"""
    # Запускаем Flask сервер для Render
    keep_alive()

    # Создаем приложение бота
    application = Application.builder().token(TOKEN).build()

    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            RATING: [MessageHandler(filters.Regex('^[⭐1-5]'), rating)],
            INTUITIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, intuitive)],
            SLOW_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, slow_action)],
            CRITICAL_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, critical_features)],
            COMPETITORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, competitors)],
            IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, improvements)],
            WISHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, wishes)],
            VIDEO: [
                MessageHandler(filters.VIDEO, video_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, video_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('admin', show_feedbacks))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('all_feedbacks', all_feedbacks_command))
    application.add_handler(CommandHandler('feedbacks_by_date', feedbacks_by_date_command))
    application.add_handler(CommandHandler('export_feedbacks', export_feedbacks_command))
    application.add_handler(CommandHandler('videos', get_videos_command))

    print("=" * 60)
    print("✅ БОТ УСПЕШНО ЗАПУЩЕН НА RENDER!")
    print("=" * 60)
    print(f"🤖 Токен: {TOKEN[:10]}...")
    print(f"🌐 Сайт: {SITE_URL}")
    print(f"👑 Админ ID: {ADMIN_IDS[0]}")
    print(f"📁 Папка видео: videos/")
    print(f"📁 Папка отзывов: feedbacks/")
    print("=" * 60)
    print("📊 Команды:")
    print("  /all_feedbacks - все отзывы с видео")
    print("  /stats - общая статистика")
    print("  /admin - последние отзывы")
    print("=" * 60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()