import uuid
import re


def normalize_name(name):
    name = re.sub(r"\s*\d{2}\.\d{2}\.\d{4}.*$", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().lower()


def merge_participants(json_users, html_users):
    merged = {}
    name_index = {}

    for u in json_users:
        uid = u["id"]
        norm = normalize_name(u["full_name"])
        u["sources"] = {"json"}
        merged[uid] = u
        name_index[norm] = uid

    for u in html_users:
        norm = normalize_name(u["full_name"])
        if norm in name_index:
            merged[name_index[norm]]["sources"].add("html")
        else:
            uid = f"html_{uuid.uuid4().hex[:8]}"
            u["id"] = uid
            u["sources"] = {"html"}
            merged[uid] = u

    return list(merged.values())
