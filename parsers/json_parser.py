import json


def parse_json(file_stream):
    data = json.load(file_stream)

    participants = {}
    mentions = set()

    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue

        from_id = msg.get("from_id")
        from_name = msg.get("from")

        if from_id and from_name and from_name != "Deleted Account" and not from_id.startswith("channel"):
            participants[from_id] = {
                "id": from_id,
                "full_name": from_name,
                "username": None
            }

        for ent in msg.get("text_entities", []):
            if ent.get("type") == "mention":
                mentions.add(ent["text"].lstrip("@"))

    return (
        list(participants.values()),
        [{"username": m} for m in mentions],
        [],
    )
