import asyncio
import time
import telebot
from telebot.types import Message
from io import BytesIO
from datetime import datetime
import re
from config import BOT_TOKEN, MAX_FILES
from parsers.json_parser import parse_json
from parsers.html_parser import parse_html
from parsers.extractor import merge_participants
from enrich.telethon_enricher import enrich_participants
from excel.exporter import generate_excel

bot = telebot.TeleBot(BOT_TOKEN)
user_files = {}
ts = int(time.time())
now = datetime.now()
date_now = now.strftime("%Y-%m-%d %H:%M:%S")

@bot.message_handler(commands=["start"])
def start(message: Message):
    bot.send_message(
        message.chat.id,
        "👋 Привет!\n\n"
        "Отправь экспорт истории чата Telegram (JSON или HTML).\n"
        f"Можно отправить до {MAX_FILES} файлов.\n\n"
        "🔒 Данные не сохраняются.\n\n"
        "После загрузки файлов следует запустить обработку командой /process\n\n"
        "Для очистки уже загруженных файлов боту следует повторно отправить команду /start"
    )
    user_files[message.chat.id] = []


@bot.message_handler(content_types=["document"])
def handle_files(message: Message):
    chat_id = message.chat.id

    user_files.setdefault(chat_id, [])

    if len(user_files[chat_id]) >= MAX_FILES:
        bot.send_message(chat_id, "❌ Превышено максимальное количество файлов.")
        return

    file_info = bot.get_file(message.document.file_id)
    file_bytes = bot.download_file(file_info.file_path)

    user_files[chat_id].append((message.document.file_name, file_bytes))
    bot.send_message(chat_id, f"📎 `{message.document.file_name}` принят", parse_mode="Markdown")


@bot.message_handler(commands=["process"])
def process_files(message: Message):
    chat_id = message.chat.id

    if not user_files.get(chat_id):
        bot.send_message(chat_id, "❌ Файлы не найдены.")
        return

    json_participants = []
    html_participants = []
    mentions_raw = []
    channels_raw = []

    for filename, file_bytes in user_files[chat_id]:
        stream = BytesIO(file_bytes)

        if filename.lower().endswith(".json"):
            p, m, c = parse_json(stream)
            json_participants.extend(p)
            mentions_raw.extend(m)
            channels_raw.extend(c)

        elif filename.lower().endswith(".html"):
            p, m, c = parse_html(stream)
            html_participants.extend(p)
            mentions_raw.extend(m)
            channels_raw.extend(c)

    participants = merge_participants(json_participants, html_participants)

    # TELETHON ENRICH
    try:
        participants = asyncio.run(enrich_participants(participants))
    except Exception:
        pass

    total_users = len(participants)

    # NORMALIZE MENTIONS
    mentions = {
        m.get("username") or m.get("full_name")
        for m in mentions_raw
        if m
    }
    mentions = [{"username": m} for m in sorted(mentions)]

    # NORMALIZE CHANNELS
    channels = {
        c.get("username")
        for c in channels_raw
        if c.get("username")
    }
    channels = [{"username": c} for c in sorted(channels)]

    if total_users < 50:

        def format_user(u):
            uname = f"@{u['username']}" if u.get("username") else "—"
            fullname = u.get("full_name", "—")
            bio = u.get("bio", "—")
            birthday = u.get("birthday", "—")
            has_channel = "✅ Да" if u.get("has_channel") else "❌ Нет"

            channel_url = u.get("channel_url")
            channel_link = (
                f"<a href='{channel_url}'>Перейти</a>"
                if channel_url else "—"
            )

            return (
                f"<b>{fullname}</b>\n"
                f"👤 {uname}\n"
                f"📝 {bio}\n"
                f"🎂 {birthday}\n"
                f"📢 Канал: {has_channel}\n"
                f"🔗 {channel_link}"
            )

        # ===== УЧАСТНИКИ =====
        users_text = "<b>👥 Участники</b>\n\n"
        users_text += "\n\n".join(format_user(u) for u in participants)

        bot.send_message(
            chat_id,
            users_text[:4096],
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        # ===== УПОМИНАНИЯ =====
        if mentions:
            mentions_text = "<b>🔔 Упоминания</b>\n"
            mentions_text += "\n".join(
                f"• {m.get('full_name') or '@' + m.get('username', '')}"
                for m in mentions
            )

            bot.send_message(
                chat_id,
                mentions_text[:4096],
                parse_mode="HTML"
            )

        # ===== КАНАЛЫ =====
        filtered_channels = [
            c for c in channels
            if c.get("username") and not re.findall(r"^\+.*", c["username"])
        ]

        if filtered_channels:
            channels_text = "<b>📺 Каналы</b>\n"
            channels_text += "\n".join(
                f"• @{c['username']}"
                for c in filtered_channels
            )

            bot.send_message(
                chat_id,
                channels_text[:4096],
                parse_mode="HTML"
            )
    else:
        excel = generate_excel(participants, mentions, channels, date_now)

        bot.send_document(
            chat_id,
            excel,
            visible_file_name=f"chat_export_{date_now}_{ts}.xlsx"
        )

    del user_files[chat_id]


bot.infinity_polling()
