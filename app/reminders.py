"""Native scheduled Telegram reminders — no n8n or paid messaging service."""
import asyncio
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from . import config, db

SCHEDULER = BackgroundScheduler(timezone=ZoneInfo('Asia/Kolkata'))


def deliver_reminder(reminder_id, chat_id, message):
    from telegram import Bot

    async def send():
        async with Bot(config.TELEGRAM_TOKEN) as bot:
            await bot.send_message(chat_id=int(chat_id), text='🔔 Gram Sahayak Reminder\n' + message)

    try:
        asyncio.run(send())
        with db.connect() as conn:
            conn.execute('UPDATE reminders SET delivered=1 WHERE id=?', (reminder_id,))
    except Exception as exc:
        print('Reminder delivery failed:', str(exc))


def schedule_reminder(chat_id, date_time_ist, message):
    if not config.TELEGRAM_TOKEN:
        raise RuntimeError('Telegram bot token not configured.')
    if not message.strip() or len(message) > 400:
        raise ValueError('Reminder text must be between 1 and 400 characters.')
    due = datetime.strptime(date_time_ist, '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    if due.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError('Reminder must be scheduled in the future.')
    rid = uuid.uuid4().hex
    with db.connect() as conn:
        conn.execute('INSERT INTO reminders(id, chat_id, message, due_utc) VALUES (?, ?, ?, ?)',
                     (rid, str(chat_id), message, due.astimezone(timezone.utc).isoformat()))
    SCHEDULER.add_job(deliver_reminder, 'date', run_date=due, args=[rid, chat_id, message], id=rid)
    return rid


def restore_reminders():
    with db.connect() as conn:
        records = conn.execute('SELECT id, chat_id, message, due_utc FROM reminders WHERE delivered=0').fetchall()
    for rec in records:
        due = datetime.fromisoformat(rec['due_utc'])
        if due > datetime.now(timezone.utc):
            SCHEDULER.add_job(deliver_reminder, 'date', run_date=due,
                              args=[rec['id'], rec['chat_id'], rec['message']],
                              id=rec['id'], replace_existing=True)


def start_scheduler():
    restore_reminders()
    if not SCHEDULER.running:
        SCHEDULER.start()
