"""Optional free Telegram channel: text, photos, voice and reminders.
Long-polling works from a Windows laptop; no webhooks or public hosting.
"""
import asyncio
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from . import config
from .api import handle_question
from .voice import transcribe, text_to_speech
from .reminders import schedule_reminder, start_scheduler

# These preferences are intentionally ephemeral (avoid saving locations without consent).
PREFS = {}


def profile(chat_id):
    return PREFS.setdefault(chat_id, {'language': 'en', 'city': ''})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🌾 Gram Sahayak / ग्राम सहायक\n'
        'Type a question, send a voice message, or share a crop photo.\n'
        '/language hi  (or /language en)\n'
        '/city Nashik\n'
        '/remind YYYY-MM-DD HH:MM reminder text  (Indian Standard Time)\n'
        'Medical questions receive general information only.')


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = (context.args[0] if context.args else '').lower()
    if language not in ('hi', 'en'):
        await update.message.reply_text('Choose /language hi or /language en')
        return
    profile(update.effective_chat.id)['language'] = language
    await update.message.reply_text(f'Language set to {language}.')


async def city_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = ' '.join(context.args).strip()
    if not city:
        await update.message.reply_text('Usage: /city Nashik')
        return
    profile(update.effective_chat.id)['city'] = city[:100]
    await update.message.reply_text(f'City set for this bot session: {city}')


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text('Usage: /remind 2026-12-01 08:30 Review weather forecast')
        return
    try:
        reminder_id = schedule_reminder(update.effective_chat.id, args[0] + ' ' + args[1], ' '.join(args[2:]))
        await update.message.reply_text('Reminder scheduled (Asia/Kolkata). ID: ' + reminder_id[:8])
    except (ValueError, RuntimeError) as exc:
        await update.message.reply_text(f'Could not schedule reminder: {exc}')


def ask(chat_id, message, image_path=''):
    pref = profile(chat_id)
    return handle_question(query=message, language=pref['language'], city=pref['city'],
                           session_id=f'tg_{chat_id}', image_path=image_path,
                           forced_route='vision' if image_path else '')


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = await asyncio.to_thread(ask, update.effective_chat.id, update.message.text)
        await update.message.reply_text(response['answer'][:4000])
    except Exception as exc:
        await update.message.reply_text(f'Unable to process request: {exc}')


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = config.UPLOADS / ('telegram_' + str(update.effective_chat.id) + '_' + str(update.message.message_id) + '.jpg')
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        await file.download_to_drive(custom_path=path)
        result = await asyncio.to_thread(ask, update.effective_chat.id,
                                         update.message.caption or 'Describe visible plant symptoms.', str(path))
        await update.message.reply_text(result['answer'][:4000])
    except Exception as exc:
        await update.message.reply_text(f'Could not analyze photograph: {exc}')
    finally:
        path.unlink(missing_ok=True)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = config.UPLOADS / ('telegram_' + str(update.effective_chat.id) + '_' + str(update.message.message_id) + '.ogg')
    try:
        audio = update.message.voice or update.message.audio
        file = await context.bot.get_file(audio.file_id)
        await file.download_to_drive(custom_path=path)
        language = profile(update.effective_chat.id)['language']
        transcript = await asyncio.to_thread(transcribe, path, language)
        if not transcript:
            await update.message.reply_text('No recognizable speech was detected.')
            return
        result = await asyncio.to_thread(ask, update.effective_chat.id, transcript)
        await update.message.reply_text(f'🗣️ {transcript}\n\n{result["answer"]}'[:4000])
        try:
            output_path = await asyncio.to_thread(text_to_speech, result['answer'], language)
            with open(output_path, 'rb') as sound:
                await update.message.reply_audio(audio=sound, filename=Path(output_path).name)
        except Exception:
            pass
    except Exception as exc:
        await update.message.reply_text(f'Voice processing unavailable: {exc}')
    finally:
        path.unlink(missing_ok=True)


def main():
    if not config.TELEGRAM_TOKEN:
        raise SystemExit('Add TELEGRAM_BOT_TOKEN to .env before starting Telegram.')
    start_scheduler()
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('language', language_command))
    application.add_handler(CommandHandler('city', city_command))
    application.add_handler(CommandHandler('remind', remind_command))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print('Telegram bot running (long polling).')
    application.run_polling(drop_pending_updates=False)


if __name__ == '__main__':
    main()
