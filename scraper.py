#!/usr/bin/env python3
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

BASE = "https://education.cau.ac.kr"
KST = timezone(timedelta(hours=9))

BOARDS = [
    {
        "id": "s0301",
        "name": "교육학과 공지",
        "desc": "education.cau.ac.kr s0301 게시판 미러",
        "out": "feed.xml",
    },
]


def parse_date(text: str) -> datetime:
    text = text.strip()
    now = datetime.now(KST)
    if m := re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", text):
        y, mo, d = map(int, m.groups())
        return datetime(y, mo, d, tzinfo=KST)
    if m := re.match(r"^(\d{1,2}):(\d{2})$", text):
        h, mi = map(int, m.groups())
        return now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if m := re.match(r"^(\d{1,2})\.(\d{1,2})$", text):
        mo, d = map(int, m.groups())
        return datetime(now.year, mo, d, tzinfo=KST)
    return now


def scrape_board(board_id: str, name: str, desc: str, out: str) -> int:
    url = f"{BASE}/bbs/board.php?bo_table={board_id}"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    fg = FeedGenerator()
    fg.title(f"중앙대 {name}")
    fg.link(href=url, rel="alternate")
    fg.description(desc)
    fg.language("ko")

    items = []
    for li in soup.select("li.list-item"):
        a = li.select_one("a.item-subject")
        if not a:
            continue
        href = a.get("href", "").replace("&amp;", "&")
        if not href:
            continue
        link = urljoin(BASE, href)

        for icon in a.select("span.wr-icon"):
            icon.decompose()
        title = " ".join(a.get_text(" ", strip=True).split())

        date_el = li.select_one("div.wr-date")
        pub = parse_date(date_el.get_text(strip=True) if date_el else "")

        author_el = li.select_one("div.wr-name .sv_member")
        author = author_el.get_text(strip=True) if author_el else "unknown"

        items.append((pub, title, link, author))

    if not items:
        raise SystemExit(f"{board_id}: no items parsed; selector may have broken")

    items.sort(key=lambda x: x[0], reverse=True)

    for pub, title, link, author in items:
        fe = fg.add_entry(order="append")
        fe.title(title)
        fe.link(href=link)
        fe.guid(link, permalink=True)
        fe.author({"name": author})
        fe.pubDate(pub)

    path = Path(out)
    if str(path.parent) != ".":
        path.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(path), pretty=True)
    return len(items)


def main():
    for b in BOARDS:
        n = scrape_board(b["id"], b["name"], b["desc"], b["out"])
        print(f"{b['id']}: {n} items -> {b['out']}")


if __name__ == "__main__":
    main()
