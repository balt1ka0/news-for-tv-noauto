#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор RSS-ленты из Markdown-файлов в папке content/.
Читает файлы, созданные Sveltia CMS, и собирает news.xml (RSS 2.0).
"""

import html
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

# === НАСТРОЙКИ ===
CONTENT_DIR = Path("content")
OUTPUT_FILE = "news.xml"

CHANNEL_TITLE = "Корпоративное ТВ — Новости"
CHANNEL_LINK = "https://balt1ka0.github.io/news-for-tv-noauto/"
CHANNEL_DESCRIPTION = "Новости науки, технологий, хайтека и умного садоводства"
CHANNEL_LANGUAGE = "ru-ru"

# Добавьте эту строку — реальный адрес самой ленты
FEED_URL = "https://balt1ka0.github.io/news-for-tv-noauto/news.xml"

DEFAULT_CATEGORY = "Новости"


def clean_text(raw) -> str:
    """Убирает лишние кавычки, HTML-теги и пробелы."""
    if raw is None:
        return ""
    text = str(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_frontmatter(text: str) -> dict:
    """Извлекает YAML-frontmatter между --- и --- (упрощённый парсер)."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    data = {}
    block = match.group(1)

    for line in block.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        # Убираем обрамляющие кавычки
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        data[key] = value

    return data


def parse_date(raw: str) -> datetime:
    """Парсит дату из ISO-формата. Если не получилось — берёт текущую."""
    if not raw:
        return datetime.now(timezone.utc)

    cleaned = str(raw).strip().strip("\"'")

    # Пробуем ISO с миллисекундами и Z (формат Sveltia)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return datetime.now(timezone.utc)


def load_news() -> list[dict]:
    """Читает все .md-файлы из папки content/."""
    if not CONTENT_DIR.exists():
        print(f"⚠ папка {CONTENT_DIR} не найдена")
        return []

    items = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"⚠ не удалось прочитать {path.name}: {exc}")
            continue

        data = parse_frontmatter(text)
        if not data.get("title"):
            print(f"⚠ пропущен файл без title: {path.name}")
            continue

        items.append(data)

    print(f"Найдено новостей: {len(items)}")
    return items


def build_rss(items: list[dict]) -> Element:
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
    atom_link.set("href", FEED_URL)
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Сортируем по дате: свежие сверху
    items_sorted = sorted(
        items,
        key=lambda x: parse_date(x.get("pub_date", "")),
        reverse=True,
    )

    for entry in items_sorted:
        title = clean_text(entry.get("title", ""))
        if not title:
            continue

        link = clean_text(entry.get("link", ""))
        node = SubElement(channel, "item")
        SubElement(node, "title").text = title
        if link:
            SubElement(node, "link").text = link
        SubElement(node, "description").text = clean_text(entry.get("summary", ""))
        SubElement(node, "pubDate").text = format_datetime(
            parse_date(entry.get("pub_date", ""))
        )
        guid = SubElement(node, "guid")
        guid.text = link or title
        if not link:
            guid.set("isPermaLink", "false")
        SubElement(node, "category").text = clean_text(
            entry.get("category", DEFAULT_CATEGORY)
        )

    return rss


def save_rss(rss: Element, path: str) -> None:
    indent(rss, space="  ")
    ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Лента сохранена: {path}")


def main() -> int:
    print("=== Генерация ленты из content/*.md ===")
    items = load_news()
    rss = build_rss(items)
    save_rss(rss, OUTPUT_FILE)
    print("=== Готово ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
