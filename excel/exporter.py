import re

import pandas as pd
from io import BytesIO


def generate_excel(participants, mentions, channels, date_now):

    def participants_df():
        return pd.DataFrame([{
            "Дата экспорта": date_now,
            "Username": f"@{u['username']}" if u.get("username") else "",
            "Имя и фамилия": u.get("full_name", ""),
            "Описание": u.get("bio", ""),
            "Дата рождения": u.get("birthday", ""),
            "Наличие канала": "Да" if u.get("has_channel") else "Нет",
            "Ссылка на канал": u.get("channel_url", "")
        } for u in participants])

    def mentions_df():
        return pd.DataFrame([{
            "Дата экспорта": date_now,
            "Username": f"@{m['username']}"
        } for m in mentions])

    def channels_df():
        return pd.DataFrame([{
            "Дата экспорта": date_now,
            "Channel": f"https://t.me/{c['username']}"
        } for c in channels if not re.findall(r"^\+.*", c['username'])])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        participants_df().to_excel(writer, "Participants", index=False)
        mentions_df().to_excel(writer, "Mentions", index=False)
        channels_df().to_excel(writer, "Channels", index=False)

    output.seek(0)
    return output
