from bs4 import BeautifulSoup
import re
from parsers.extractor import normalize_name


def parse_html(file_stream):
    soup = BeautifulSoup(file_stream.read(), "lxml")

    participants = {}
    mentions = set()
    channels = set()

    for msg in soup.select("div.message.default"):
        from_name = msg.select_one(".from_name")
        if from_name:
            raw_name = from_name.get_text(" ", strip=True)

            # forwarded from channel with date → skip
            if not re.search(r"\d{2}\.\d{2}\.\d{4}", raw_name):
                clean = normalize_name(raw_name)
                participants[clean] = {
                    "id": clean,
                    "full_name": raw_name,
                    "username": None
                }

        text = msg.select_one(".text")
        if not text:
            continue

        for a in text.select("a"):
            href = a.get("href", "")
            label = a.get_text(strip=True)

            if not href.startswith("https://t.me/"):
                continue

            value = href.split("/")[-1]

            if label.startswith("@"):
                mentions.add(value)
            else:
                channels.add(value)

    return (
        list(participants.values()),
        [{"username": m} for m in mentions],
        [{"username": c} for c in channels],
    )
