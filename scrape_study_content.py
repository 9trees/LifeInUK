#!/usr/bin/env python3
"""Scrape full study content (text + images) from the live LITUK site.

Authenticates with credentials in .env, iterates known study pages,
captures ordered content blocks (headings, paragraphs, bullets, images,
tables), downloads referenced images locally, and writes study_content.json.

Output schema:
{
  "topic_names": { "1": "...", ... },
  "pages": [
    {
      "id": "1_1", "topic_code": 1, "sequence_no": 1, "title": "...",
      "blocks": [
        {"type": "heading", "level": 2, "text": "..."},
        {"type": "paragraph", "text": "..."},
        {"type": "bullets", "items": ["...", "..."]},
        {"type": "image", "src": "assets/study/img_p79.jpg", "alt": "..."},
        {"type": "table", "rows": [["a","b"], ...]}
      ]
    }
  ]
}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "study"
OUT = ROOT / "study_content.json"

SITE_ROOT = "https://www.officiallifeintheuk.co.uk"
LOGIN_URL = f"{SITE_ROOT}/lz/myaccount/login"
STUDY_URL_TMPL = f"{SITE_ROOT}/lz/lituk/study/{{topic}}/{{section}}"

TOPIC_NAMES = {
    "1": "The values and principles of the UK",
    "2": "What is the UK?",
    "3": "A long and illustrious history",
    "4": "A modern, thriving society",
    "5": "The UK government, the law and your role",
}

# Known page set, derived from source files 1_1 ... 5_8.
PAGE_SET = [
    (1, 1), (1, 2), (1, 3), (1, 4),
    (2, 1),
    (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7),
    (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
    (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8),
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def login(page, username: str, password: str) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    if "/lz/lituk" in page.url or "logout" in page.content().lower():
        return

    page.locator('input[type="email"], input[name*="email" i], input[type="text"]').first.fill(username)
    page.locator('input[type="password"]').first.fill(password)
    for selector in [
        'button:has-text("Log in")',
        'button:has-text("Login")',
        'input[type="submit"]',
        'button[type="submit"]',
    ]:
        loc = page.locator(selector)
        if loc.count() > 0:
            loc.first.click()
            break
    page.wait_for_load_state("domcontentloaded")


def scrape_blocks(page, topic: int, section: int) -> dict:
    page.goto(STUDY_URL_TMPL.format(topic=topic, section=section), wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    return page.evaluate(
        """
        () => {
          const section = document.querySelector('section.lituk.study-section') || document.querySelector('.study-section');
          if (!section) return { found: false };

          const bodyEl = section.querySelector('.body.study, .body.outerWrapper.study') || section;
          const mainCol = bodyEl.querySelector('.col_3_4') || bodyEl;

          const blocks = [];
          const titleEl = mainCol.querySelector('h2, h1');
          const title = (titleEl ? titleEl.innerText : '').trim();

          const walk = (node) => {
            node.childNodes.forEach((child) => {
              if (child.nodeType !== 1) return;
              const tag = child.tagName.toLowerCase();

              if (/^h[1-4]$/.test(tag)) {
                const text = child.innerText.trim();
                if (text) blocks.push({ type: 'heading', level: Number(tag[1]), text });
              } else if (tag === 'p') {
                const img = child.querySelector('img');
                const text = child.innerText.trim();
                if (text) blocks.push({ type: 'paragraph', text });
                if (img) blocks.push({ type: 'image', src: img.getAttribute('src'), alt: img.getAttribute('alt') || '' });
              } else if (tag === 'ul' || tag === 'ol') {
                const items = Array.from(child.querySelectorAll(':scope > li')).map(li => li.innerText.trim()).filter(Boolean);
                if (items.length) blocks.push({ type: 'bullets', ordered: tag === 'ol', items });
              } else if (tag === 'img') {
                blocks.push({ type: 'image', src: child.getAttribute('src'), alt: child.getAttribute('alt') || '' });
              } else if (tag === 'figure') {
                const img = child.querySelector('img');
                const cap = child.querySelector('figcaption');
                if (img) blocks.push({ type: 'image', src: img.getAttribute('src'), alt: (cap ? cap.innerText.trim() : (img.getAttribute('alt') || '')) });
              } else if (tag === 'table') {
                const rows = Array.from(child.querySelectorAll('tr')).map(tr =>
                  Array.from(tr.querySelectorAll('th,td')).map(td => td.innerText.trim())
                );
                if (rows.length) blocks.push({ type: 'table', rows });
              } else if (child.children.length) {
                walk(child);
              }
            });
          };

          walk(mainCol);
          return { found: true, title, blocks };
        }
        """
    )


def safe_asset_name(src: str) -> str:
    path = urlparse(src).path
    name = Path(path).name or "image"
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name


def download_image(context, src: str) -> str | None:
    absolute = urljoin(SITE_ROOT + "/", src.lstrip("/")) if not src.startswith("http") else src
    try:
        response = context.request.get(absolute)
        if not response.ok:
            return None
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        name = safe_asset_name(src)
        (ASSET_DIR / name).write_bytes(response.body())
        return f"assets/study/{name}"
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    env = load_env(ROOT / ".env")
    username = env.get("Base_URL_USERNAME") or env.get("USERNAME") or env.get("EMAIL")
    password = env.get("Base_URL_PASSWORD") or env.get("PASSWORD")
    if not username or not password:
        raise RuntimeError(".env must contain Base_URL_USERNAME and Base_URL_PASSWORD")

    pages = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(25000)

        login(page, username, password)

        for topic, section in PAGE_SET:
            result = scrape_blocks(page, topic, section)
            if not result.get("found"):
                print(f"WARN: study/{topic}/{section} content not found")
                continue

            blocks = result.get("blocks", [])
            for block in blocks:
                if block.get("type") == "image" and block.get("src"):
                    local = download_image(context, block["src"])
                    if local:
                        block["src"] = local

            title = result.get("title") or f"Topic {topic} - Page {section}"
            pages.append(
                {
                    "id": f"{topic}_{section}",
                    "topic_code": topic,
                    "sequence_no": section,
                    "title": title,
                    "blocks": blocks,
                }
            )
            image_count = sum(1 for b in blocks if b.get("type") == "image")
            print(f"study/{topic}/{section}: {len(blocks)} blocks, {image_count} images")

        context.close()
        browser.close()

    payload = {"topic_names": TOPIC_NAMES, "pages": pages}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.name} with {len(pages)} pages.")


if __name__ == "__main__":
    main()
