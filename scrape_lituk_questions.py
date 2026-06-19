import json
import time
import argparse
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_URL = "https://www.officiallifeintheuk.co.uk/"
LOGIN_URL = "https://www.officiallifeintheuk.co.uk/lz/myaccount/login"
DASHBOARD_URL = "https://www.officiallifeintheuk.co.uk/lz/lituk"
PRACTICE_TOPICS_URL = "https://www.officiallifeintheuk.co.uk/lz/lituk/practice/topics"

TOPICS = [
    "The values and principles of the UK",
    "What is the UK?",
    "A long and illustrious history",
    "A modern, thriving society",
    "The UK government, the law and your role",
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def click_first(page, selectors: list[str], timeout_ms: int = 7000) -> bool:
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() == 0:
            continue
        try:
            loc.first.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def login_if_needed(page, username: str, password: str) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    # If already signed in, this page may redirect to account/dashboard.
    if "logout" in page.content().lower() or "/lz/lituk" in page.url:
        return

    email_box = None
    label_box = page.get_by_label("Username or email")
    if label_box.count() > 0:
        email_box = label_box.first
    else:
        email_sel = [
            'input[type="email"]',
            'input[name*="email" i]',
            'input[name*="user" i]',
            'input[type="text"]',
        ]
        for sel in email_sel:
            loc = page.locator(sel)
            if loc.count() > 0:
                email_box = loc.first
                break
    if email_box is None:
        raise RuntimeError("Could not find username/email input on login page.")

    pass_box = None
    label_pass = page.get_by_label("Password")
    if label_pass.count() > 0:
        pass_box = label_pass.first
    else:
        pass_sel = [
            'input[type="password"]',
            'input[name*="pass" i]',
        ]
        for sel in pass_sel:
            loc = page.locator(sel)
            if loc.count() > 0:
                pass_box = loc.first
                break
    if pass_box is None:
        raise RuntimeError("Could not find password input on login page.")

    email_box.fill(username)
    pass_box.fill(password)

    if not click_first(
        page,
        [
            'button:has-text("Log in")',
            'button:has-text("Login")',
            'input[type="submit"]',
            'button[type="submit"]',
        ],
    ):
        raise RuntimeError("Could not find login submit button.")

    page.wait_for_load_state("domcontentloaded")
    if "/lz/myaccount/login" in page.url:
        raise RuntimeError("Login did not succeed. Still on login page.")


def start_all_topics_all_questions(page) -> None:
    page.goto(DASHBOARD_URL, wait_until="domcontentloaded")

    # Some accounts show a "Start learning" CTA first.
    click_first(
        page,
        [
            'a:has-text("Start learning")',
            'button:has-text("Start learning")',
        ],
        timeout_ms=3000,
    )

    page.goto(PRACTICE_TOPICS_URL, wait_until="domcontentloaded")

    # Build and start one combined test from all topic question IDs directly.
    started = page.evaluate(
        """
        (topicTitles) => {
            if (!window.TOPICLIST || !Array.isArray(window.TOPICLIST.topics) || !window.Test) {
                return { ok: false, reason: 'Missing TOPICLIST/Test globals' };
            }

            // Avoid layout-specific scrolling logic that can fail in headless runs.
            if (window.Test && window.Test.prototype) {
                window.Test.prototype.scrollUp = function() {};
            }

            const selectedTopics = window.TOPICLIST.topics.filter(
                t => topicTitles.includes(t.title)
            );
            const ids = [];
            for (const t of selectedTopics) {
                const qids = Array.isArray(t.questionsId) ? t.questionsId : [];
                for (const qid of qids) ids.push(qid);
            }

            const uniq = Array.from(new Set(ids));
            if (!uniq.length) {
                return { ok: false, reason: 'No question IDs found for selected topics' };
            }

            const options = {
                section: 'body',
                subsection: 'body',
                selector: 'body',
                enableExplanation: true,
                enableExplanationCode: false,
                enableFlagging: true,
                enableReview: false,
                enablePause: false,
                enableTopicResults: false,
                shuffleQuestions: false,
                forceAudio: false,
                autoPlayAudio: false,
            };

            window.TEST = new window.Test(options);
            for (const qid of uniq) {
                window.TEST.addQuestionId(qid);
            }
            window.TEST.start();

            return { ok: true, count: uniq.length };
        }
        """,
        TOPICS,
    )

    if not started or not started.get("ok"):
        reason = started.get("reason") if isinstance(started, dict) else "unknown"
        raise RuntimeError(f"Could not start all-questions test via JS: {reason}")

    page.wait_for_selector('a:has-text("Next"), button:has-text("Next")', timeout=10000)


def read_current_question(page) -> dict:
    data = page.evaluate(
        """
        () => {
          const t = window.TEST;
          if (!t || !t.questions || !t.questions.length) return null;
          const q = t.questions[t.index];
          if (!q) return null;
          const answers = (q.answers || []).map((a, idx) => ({
            index: idx,
            text: a.text,
            correct: !!a.correct
          }));
          return {
            topic: q.topic,
                        question: { text: q.text },
                        answers: answers.map(a => ({ correct: a.correct, text: a.text })),
                        explanation: { text: q.explanation ? q.explanation.text : "" },
                        _meta: {
                            position: t.index + 1,
                            total: (t.questionsId || []).length,
                            id: q.id
                        },
            correct_indices: answers.filter(a => a.correct).map(a => a.index),
          };
        }
        """
    )
    if data is None:
        raise RuntimeError("Could not read question from window.TEST.")
    return data


def select_correct_answers(page, correct_indices: list[int]) -> None:
    # Answer checkboxes appear in the same order as q.answers.
    boxes = page.locator('input[type="checkbox"]:visible')
    count = boxes.count()
    if count == 0:
        raise RuntimeError("No visible answer checkboxes found.")

    for idx in correct_indices:
        if idx < count:
            try:
                boxes.nth(idx).click(timeout=2000)
            except Exception:
                # Fallback: click answer text by position label if checkbox click fails.
                option_prefix = chr(ord("A") + idx)
                click_first(
                    page,
                    [f'text={option_prefix})'],
                    timeout_ms=1500,
                )


def go_next_question(page) -> bool:
    current_position = page.evaluate("() => window.TEST ? window.TEST.index : -1")
    if not click_first(
        page,
        [
            'a:has-text("Next")',
            'button:has-text("Next")',
            'text=Next',
        ],
        timeout_ms=5000,
    ):
        return False

    # Wait until index changes, or test has ended.
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            new_position = page.evaluate("() => window.TEST ? window.TEST.index : -1")
            if new_position != current_position:
                return True
        except Exception:
            pass
        time.sleep(0.15)

    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape LITUK practice questions to JSON.")
    parser.add_argument("--output", default="lituk_questions_422.json", help="Output JSON path")
    parser.add_argument(
        "--max-questions",
        type=int,
        default=0,
        help="Optional cap for debugging (0 means no cap).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.2,
        help="Delay between questions to reduce server load.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError(".env not found in current directory.")

    env = load_env(env_path)
    username = env.get("USERNAME") or env.get("EMAIL")
    password = env.get("PASSWORD")
    if not username or not password:
        raise RuntimeError(".env must contain USERNAME and PASSWORD.")

    output_path = Path(args.output)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.set_default_timeout(10000)
            print("Opening site and logging in...")
            page.goto(BASE_URL, wait_until="domcontentloaded")
            login_if_needed(page, username, password)
            print("Starting practice with all topics and all questions...")
            start_all_topics_all_questions(page)

            questions: list[dict] = []
            seen_ids: set[str] = set()

            while True:
                q = read_current_question(page)
                qid = q["_meta"]["id"]

                if qid in seen_ids:
                    # Loop detected; likely reached end/result screen and returned.
                    break

                seen_ids.add(qid)
                questions.append(q)
                if len(questions) % 10 == 0 or len(questions) <= 3:
                    print(
                        f"Captured {len(questions)} / {q['_meta']['total']} - "
                        f"{q['_meta']['id']} (Q{q['_meta']['position']})"
                    )

                select_correct_answers(page, q["correct_indices"])

                moved = go_next_question(page)
                if not moved:
                    break

                if args.delay_seconds > 0:
                    time.sleep(args.delay_seconds)

                # Stop once full bank is collected.
                if len(questions) >= q["_meta"]["total"]:
                    break

                if args.max_questions > 0 and len(questions) >= args.max_questions:
                    print(f"Reached debug limit: {args.max_questions}")
                    break

            final_questions = [
                {
                    "topic": item["topic"],
                    "question": item["question"],
                    "answers": item["answers"],
                    "explanation": item["explanation"],
                }
                for item in questions
            ]

            output_path.write_text(
                json.dumps(final_questions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved {len(questions)} questions to {output_path}")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except PlaywrightTimeoutError as exc:
        print(f"Playwright timeout: {exc}")
        raise
