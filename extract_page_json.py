#!/usr/bin/env python3
"""
Extract embedded JSON from a webpage and save it to a file.

This is useful for pages where question data is rendered from JSON with extra metadata.

Examples:
  python extract_page_json.py "https://www.officiallifeintheuk.co.uk/lz/lituk/practice/topics"
  python extract_page_json.py "https://example.com" -o question.json
  python extract_page_json.py "https://example.com" --all -o all_candidates.json
  python extract_page_json.py "https://example.com" --cookie "sessionid=...; csrftoken=..."
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_BLOCK_RE = re.compile(
    r"<script[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL
)

# Handles common assignment patterns used by SSR/SPA apps.
ASSIGNMENT_PATTERNS = [
    re.compile(r"__NEXT_DATA__\s*=\s*(\{.*?\})\s*;", re.DOTALL),
    re.compile(r"__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;", re.DOTALL),
    re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\})\s*;", re.DOTALL),
    re.compile(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;", re.DOTALL),
]


@dataclass
class JsonCandidate:
    source: str
    data: Any
    score: int


def fetch_html(url: str, user_agent: str, cookie: str | None = None) -> str:
    req = Request(url)
    req.add_header("User-Agent", user_agent)
    req.add_header("Accept", "text/html,application/xhtml+xml")
    if cookie:
        req.add_header("Cookie", cookie)

    with urlopen(req, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read()
        charset = "utf-8"
        if "charset=" in content_type.lower():
            charset = content_type.split("charset=")[-1].split(";")[0].strip()
        return raw.decode(charset, errors="replace")


def try_json_load(s: str) -> Any | None:
    s = s.strip()
    if not s:
        return None
    if not (s.startswith("{") or s.startswith("[")):
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def candidate_score(value: Any) -> int:
    """Score likely question payloads higher than generic config blobs."""
    score = 0

    def walk(v: Any, depth: int = 0) -> None:
        nonlocal score
        if depth > 5:
            return
        if isinstance(v, dict):
            keys = {str(k).lower() for k in v.keys()}
            interesting = {
                "question",
                "questions",
                "answer",
                "answers",
                "options",
                "choices",
                "explanation",
                "topic",
                "metadata",
            }
            score += len(keys & interesting) * 6
            if "question" in keys and "answers" in keys:
                score += 20
            for child in v.values():
                walk(child, depth + 1)
        elif isinstance(v, list):
            if v:
                score += min(len(v), 5)
            for child in v[:25]:
                walk(child, depth + 1)

    walk(value)
    return score


def extract_json_candidates(html_text: str) -> list[JsonCandidate]:
    candidates: list[JsonCandidate] = []

    # 1) Raw JSON script blocks.
    for i, raw_script in enumerate(SCRIPT_BLOCK_RE.findall(html_text), start=1):
        script = html.unescape(raw_script.strip())
        parsed = try_json_load(script)
        if parsed is not None:
            candidates.append(
                JsonCandidate(
                    source=f"script_block_{i}",
                    data=parsed,
                    score=candidate_score(parsed),
                )
            )

        # 2) Common JS variable assignments containing JSON objects.
        for pattern in ASSIGNMENT_PATTERNS:
            for match in pattern.finditer(script):
                raw_obj = match.group(1)
                parsed_assigned = try_json_load(raw_obj)
                if parsed_assigned is not None:
                    candidates.append(
                        JsonCandidate(
                            source=f"script_block_{i}:{pattern.pattern[:30]}",
                            data=parsed_assigned,
                            score=candidate_score(parsed_assigned),
                        )
                    )

    # 3) De-duplicate by normalized JSON representation.
    unique: dict[str, JsonCandidate] = {}
    for c in candidates:
        try:
            key = json.dumps(c.data, sort_keys=True, separators=(",", ":"))
        except TypeError:
            # Non-serializable objects are unlikely here, but skip if encountered.
            continue
        if key not in unique or c.score > unique[key].score:
            unique[key] = c

    return sorted(unique.values(), key=lambda c: c.score, reverse=True)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a webpage, extract embedded JSON, and save to file."
    )
    parser.add_argument("url", help="Page URL")
    parser.add_argument(
        "-o",
        "--output",
        default="question_payload.json",
        help="Output JSON file (default: question_payload.json)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Save all discovered JSON candidates instead of only the best match.",
    )
    parser.add_argument(
        "--cookie",
        default=None,
        help="Optional Cookie header for authenticated pages.",
    )
    parser.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        ),
        help="HTTP User-Agent",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    try:
        html_text = fetch_html(args.url, user_agent=args.user_agent, cookie=args.cookie)
    except HTTPError as e:
        print(f"HTTP error: {e.code} {e.reason}", file=sys.stderr)
        return 2
    except URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Unexpected fetch error: {e}", file=sys.stderr)
        return 2

    candidates = extract_json_candidates(html_text)
    if not candidates:
        print(
            "No embedded JSON found in <script> blocks. "
            "This page may load data via XHR/fetch after render.",
            file=sys.stderr,
        )
        return 1

    out_path = Path(args.output)

    if args.all:
        payload = [
            {"source": c.source, "score": c.score, "data": c.data}
            for c in candidates
        ]
        save_json(out_path, payload)
        print(f"Saved {len(payload)} JSON candidates to: {out_path}")
    else:
        best = candidates[0]
        save_json(out_path, best.data)
        print(f"Saved best candidate (source={best.source}, score={best.score}) to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
