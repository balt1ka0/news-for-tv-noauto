#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор RSS-ленты из ручного JSON.
Читает manual_news.json и собирает news.xml в формате RSS 2.0.
"""

import html
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

# === НАСТРОЙКИ ===
INPUT_FILE = "manual_news.json"
OUTPUT_FILE = "news.xml"

CHANNEL_TITLE = "Корпоративное ТВ — Новости"
CHANNEL_LINK = "https://tv.example.com"
CHANNEL_DESCRIPTION = "Новости науки, технологий, хайтека и умного садоводства"
CHANNEL_LANGUAGE = "ru-ru"

DEFAULT_CATEGORY = "Новости"


def clean_text(raw: str) -> str:
    """Убирает HTML-теги и лишние пробелы."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(raw: str) -> datetime:
    """Парсит дату из ISO-формата. Если не получилось — берет текущую."""
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def load_news() -> list[dict]:
    """Читает JSON-файл с новостями."""
    path = Path(INPUT_FILE)
    if not path.exists():
        print(f"⚠ файл {INPUT_FILE} не найден — лента будет пустой")
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ ошибка в JSON: {exc}")
        sys.exit(1)

    if not isinstance(data, list):
        print("❌ JSON должен быть массивом [...]")
        sys.exit(1)

    return data


def build_rss(items: list[dict]) -> Element:
    """Формирует RSS 2.0 из списка новостей."""
    rss = Element("rss", {
        "version": "2.0",
        "xmlns:atom": "http://www.w3.org/2005/Atom",
    })
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = CHANNEL_TITLE
    SubElement(channel, "link").text = CHANNEL_LINK
    SubElement(channel, "description").text = CHANNEL_DESCRIPTION
    SubElement(channel, "language").text = CHANNEL_LANGUAGE
    SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )
    SubElement(channel, "generator").text = "corp-tv-manual-feed"

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{CHANNEL_LINK}/news.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Сортируем по дате: свежие сверху
    items_sorted = sorted(items, key=lambda x: parse_date(x.get("pub_date", "")), reverse=True)

    for entry in items_sorted:
        title = clean_text(entry.get("title", ""))
        if not title:
            continue  # пропускаем записи без заголовка

        node = SubElement(channel, "item")
        SubElement(node, "title").text = title
        SubElement(node, "link").text = entry.get("link", "").strip()
        SubElement(node, "description").text = clean_text(entry.get("summary", ""))
        SubElement(node, "pubDate").text = format_datetime(
            parse_date(entry.get("pub_date", ""))
        )
        SubElement(node, "guid").text = entry.get("link", title)
        SubElement(node, "category").text = entry.get("category", DEFAULT_CATEGORY)

    return rss


def save_rss(rss: Element, path: str) -> None:
    """Сохраняет XML с отступами."""
    indent(rss, space="  ")
    ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Лента сохранена: {path}")


def main() -> int:
    print("=== Генерация ленты из manual_news.json ===")
    items = load_news()
    print(f"Новостей в JSON: {len(items)}")

    rss = build_rss(items)
    save_rss(rss, OUTPUT_FILE)
    print("=== Готово ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())