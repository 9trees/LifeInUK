#!/usr/bin/env python3
"""Build Study JSON datasets from source MHTML files.

DEPRECATED for study_content.json: study pages are now scraped live from the
official site (with images and full block structure) via scrape_study_content.py.
This script is retained only to regenerate study_plan.json from the saved
study-plan MHTML file.

Outputs:
- study_content.json: (legacy) normalized study pages grouped by topic/sequence
- study_plan.json: study-plan checklist items
"""

from __future__ import annotations

import email
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_BACK = ROOT / "web_back"
STUDY_OUT = ROOT / "study_content.json"
PLAN_OUT = ROOT / "study_plan.json"

WEEK_PATTERN = re.compile(r"^Week\s+(\d+)\s*-\s*(.+)$", re.IGNORECASE)


def read_mhtml_html(path: Path) -> str:
    msg = email.message_from_bytes(path.read_bytes())
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    raise ValueError(f"No text/html part found in {path}")


def clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_study_body(html_doc: str) -> str:
    body_match = re.search(r'<div class="body outerWrapper study">([\s\S]*?)</div>\s*</div>\s*</section>', html_doc, re.IGNORECASE)
    if not body_match:
        raise ValueError("Study body container not found")

    section = body_match.group(1)
    main_col = re.search(r'<div class="col_3_4">([\s\S]*?)</div>\s*</div>\s*<!-- controls -->', section, re.IGNORECASE)
    if main_col:
        section = main_col.group(1)

    # Drop script/style blocks and comments.
    section = re.sub(r"<script[\s\S]*?</script>", "", section, flags=re.IGNORECASE)
    section = re.sub(r"<style[\s\S]*?</style>", "", section, flags=re.IGNORECASE)
    section = re.sub(r"<!--[\s\S]*?-->", "", section)
    return section


def extract_study_page(path: Path) -> dict:
    html_doc = read_mhtml_html(path)
    file_match = re.match(r"(\d+)_(\d+)\.mhtml$", path.name)
    if not file_match:
        raise ValueError(f"Unexpected study file name: {path.name}")

    topic_code = int(file_match.group(1))
    seq_no = int(file_match.group(2))

    body = find_study_body(html_doc)

    title_match = re.search(r"<h2[^>]*>(.*?)</h2>", body, flags=re.IGNORECASE | re.DOTALL)
    title = clean_text(title_match.group(1)) if title_match else f"Topic {topic_code} - Page {seq_no}"

    content_blocks = []
    for tag_name, inner_html in re.findall(r"<(p|li)[^>]*>(.*?)</\1>", body, flags=re.IGNORECASE | re.DOTALL):
        text = clean_text(inner_html)
        if not text:
            continue
        block_type = "bullet" if tag_name.lower() == "li" else "paragraph"
        content_blocks.append({"type": block_type, "text": text})

    if not content_blocks:
        fallback_text = clean_text(body)
        if fallback_text:
            content_blocks.append({"type": "paragraph", "text": fallback_text})

    return {
        "id": f"{topic_code}_{seq_no}",
        "topic_code": topic_code,
        "sequence_no": seq_no,
        "title": title,
        "source_file": path.name,
        "content_blocks": content_blocks,
    }


def extract_plan_items(path: Path) -> list[dict]:
    html_doc = read_mhtml_html(path)
    article_match = re.search(r"<article[^>]*>([\s\S]*?)</article>", html_doc, re.IGNORECASE)
    article = article_match.group(1) if article_match else html_doc

    article = re.sub(r"<script[\s\S]*?</script>", "", article, flags=re.IGNORECASE)
    article = re.sub(r"<style[\s\S]*?</style>", "", article, flags=re.IGNORECASE)
    article = re.sub(r"<!--[\s\S]*?-->", "", article)

    lines = [clean_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", article, flags=re.IGNORECASE | re.DOTALL)]
    bullets = [clean_text(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", article, flags=re.IGNORECASE | re.DOTALL)]

    items = []
    current_week = 0
    order_no = 0

    for line in lines:
        if not line:
            continue
        week_match = WEEK_PATTERN.match(line)
        if week_match:
            current_week = int(week_match.group(1))
            order_no += 1
            items.append(
                {
                    "id": f"plan_{order_no}",
                    "week_no": current_week,
                    "order_no": order_no,
                    "title": line,
                    "description": f"Focus area: {week_match.group(2).strip()}",
                }
            )
            continue

        if current_week and (line[0].isdigit() or line.lower().startswith("start") or line.lower().startswith("once")):
            order_no += 1
            items.append(
                {
                    "id": f"plan_{order_no}",
                    "week_no": current_week,
                    "order_no": order_no,
                    "title": line,
                    "description": "Weekly study action",
                }
            )

    # Add a short set of learning habit bullets as week 0 prep tasks.
    prep_bullets = [b for b in bullets if b and len(items) < 200][:6]
    for bullet in prep_bullets:
        order_no += 1
        items.append(
            {
                "id": f"plan_{order_no}",
                "week_no": 0,
                "order_no": order_no,
                "title": bullet,
                "description": "Preparation habit",
            }
        )

    # De-duplicate by title while preserving order.
    seen = set()
    deduped = []
    for item in items:
        key = item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def main() -> None:
    page_paths = sorted(WEB_BACK.glob("[1-5]_[0-9]*.mhtml"), key=lambda p: [int(x) for x in p.stem.split("_")])
    if not page_paths:
        raise SystemExit("No study page MHTML files found.")

    pages = [extract_study_page(path) for path in page_paths]

    by_topic = {}
    for page in pages:
        topic = str(page["topic_code"])
        by_topic.setdefault(topic, []).append(page)

    for topic_pages in by_topic.values():
        topic_pages.sort(key=lambda p: p["sequence_no"])

    topic_names = {
        "1": "The values and principles of the UK",
        "2": "What is the UK?",
        "3": "A long and illustrious history",
        "4": "A modern, thriving society",
        "5": "The UK government, the law and your role",
    }

    study_payload = {
        "topic_names": topic_names,
        "pages": pages,
    }

    plan_source = WEB_BACK / "Example Life in the UK Study Plan _ Official Life in the UK Learning Zone.mhtml"
    plan_items = extract_plan_items(plan_source)

    STUDY_OUT.write_text(json.dumps(study_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PLAN_OUT.write_text(json.dumps({"items": plan_items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {STUDY_OUT.name} with {len(pages)} pages.")
    print(f"Wrote {PLAN_OUT.name} with {len(plan_items)} items.")


if __name__ == "__main__":
    main()
