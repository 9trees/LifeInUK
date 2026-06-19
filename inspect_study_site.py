#!/usr/bin/env python3
"""Authenticated inspection of the LITUK study pages.

Logs in using credentials from .env, visits a few study pages, and dumps:
- the study-section outer HTML
- image references (src/alt)
- text block structure

This is a research helper to mirror the real study UI faithfully.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "study_site_inspection.json"

LOGIN_URL = "https://www.officiallifeintheuk.co.uk/lz/myaccount/login"
STUDY_URL_TMPL = "https://www.officiallifeintheuk.co.uk/lz/lituk/study/{topic}/{section}"

# Pages to inspect (topic, section).
SAMPLE_PAGES = [(1, 1), (1, 2), (3, 1), (4, 4)]


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

    email = page.locator('input[type="email"], input[name*="email" i], input[type="text"]').first
    email.fill(username)

    pwd = page.locator('input[type="password"]').first
    pwd.fill(password)

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


def inspect_page(page, topic: int, section: int) -> dict:
    page.goto(STUDY_URL_TMPL.format(topic=topic, section=section), wait_until="domcontentloaded")
    page.wait_for_timeout(800)

    data = page.evaluate(
        """
        () => {
          const section = document.querySelector('section.lituk.study-section') || document.querySelector('.study-section');
          if (!section) return { found: false };

          const bodyEl = section.querySelector('.body.study, .body.outerWrapper.study') || section;
          const mainCol = bodyEl.querySelector('.col_3_4') || bodyEl;

          const images = Array.from(mainCol.querySelectorAll('img')).map(img => ({
            src: img.getAttribute('src'),
            alt: img.getAttribute('alt') || '',
            width: img.getAttribute('width') || '',
            height: img.getAttribute('height') || ''
          }));

          const blocks = [];
          mainCol.querySelectorAll('h1,h2,h3,h4,p,li,img,table,figure,figcaption').forEach(el => {
            const tag = el.tagName.toLowerCase();
            if (tag === 'img') {
              blocks.push({ type: 'image', src: el.getAttribute('src'), alt: el.getAttribute('alt') || '' });
            } else if (tag === 'table') {
              blocks.push({ type: 'table', html: el.outerHTML });
            } else {
              const text = (el.innerText || '').trim();
              if (text) blocks.push({ type: tag, text });
            }
          });

          const title = (mainCol.querySelector('h2, h1')?.innerText || '').trim();

          return {
            found: true,
            url: location.href,
            title,
            images,
            blockCount: blocks.length,
            blocks: blocks.slice(0, 60),
            outerHtmlSample: mainCol.outerHTML.slice(0, 4000)
          };
        }
        """
    )
    data["topic"] = topic
    data["section"] = section
    return data


def main() -> None:
    env = load_env(ROOT / ".env")
    username = env.get("Base_URL_USERNAME") or env.get("USERNAME") or env.get("EMAIL")
    password = env.get("Base_URL_PASSWORD") or env.get("PASSWORD")
    if not username or not password:
        raise RuntimeError(".env must contain Base_URL_USERNAME and Base_URL_PASSWORD")

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(20000)

        login(page, username, password)
        for topic, section in SAMPLE_PAGES:
            try:
                results.append(inspect_page(page, topic, section))
            except Exception as exc:  # noqa: BLE001
                results.append({"topic": topic, "section": section, "found": False, "error": str(exc)})

        context.close()
        browser.close()

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.name} with {len(results)} page inspections.")
    for r in results:
        print(r.get("topic"), r.get("section"), "found=", r.get("found"), "images=", len(r.get("images", [])))


if __name__ == "__main__":
    main()
