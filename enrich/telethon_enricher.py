from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import FloodWaitError
import asyncio
from config import TELETHON_API_ID, TELETHON_API_HASH, TELETHON_SESSION

client = TelegramClient(TELETHON_SESSION, TELETHON_API_ID, TELETHON_API_HASH)


async def enrich_participants(participants):
    enriched = []

    async with client:
        for u in participants:
            uid = u.get("id")

            if not isinstance(uid, str) or not uid.startswith("user"):
                enriched.append(u)
                continue

            try:
                user_id = int(uid.replace("user", ""))
                full = await client(GetFullUserRequest(user_id))

                def extract_personal_channel(full):
                    channel_id = full.full_user.personal_channel_id
                    if not channel_id:
                        return None

                    for chat in full.chats:
                        if getattr(chat, "id", None) == channel_id:
                            if getattr(chat, "username", None):
                                return f"https://t.me/{chat.username}"

                    return None

                personal_channel = extract_personal_channel(full)

                user = full.users[0]
                full_user = full.full_user

                enriched.append({
                    **u,
                    "username": user.username,
                    "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                    "bio": full_user.about,
                    "has_channel": bool(personal_channel),
                    "channel_url": personal_channel,
                    "birthday": (
                        f"{full_user.birthday.day:02d}."
                        f"{full_user.birthday.month:02d}."
                        f"{full_user.birthday.year}"
                        if full_user.birthday else None
                    )
                })

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                enriched.append(u)

            except Exception as e:
                enriched.append(u)

    return enriched
