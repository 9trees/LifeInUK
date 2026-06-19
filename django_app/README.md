# Life in the UK — Django App

Django implementation per `Plan.txt` and the `docx/` architecture.

## Apps
- `accounts` — custom email user, register/login/logout, profile + password change, 30-day active window (middleware + banner context processor)
- `content` — `Topic`, `StudyPage` (JSON content blocks), `StudyPlanItem` + import commands
- `study` — study reader (rich blocks incl. images/tables), sequential nav, progress tracking
- `practice` — `Question`/`AnswerOption`/`PracticeSession`/`PracticeResponse`, topic + mode selection (random 10/20/30/all/unanswered), one-at-a-time flow with explanation
- `mocktest` — blueprint generator (24 Q), 45-min timer, auto-submit, behavior events, pass mark 18
- `analytics` — dashboard with Bootstrap 5 + Chart.js (topic accuracy, mock trend, weakest topic)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd django_app
python manage.py migrate
python manage.py import_topics
python manage.py import_study        # loads study_content.json (with images)
python manage.py import_study_plan   # loads study_plan.json
python manage.py import_questions    # loads lituk_questions_422.json
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and register.

## Configuration
Environment variables (optional, read from repo-root `.env`):
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG` (default True)
- `DATABASE_URL` (default SQLite; set a Postgres URL for production)
- `ACTIVE_WINDOW_DAYS` (default 30)

## Data sources
- `study_content.json` + `assets/study/*.jpg` — scraped from the live site (`scrape_study_content.py`)
- `study_plan.json` — `build_study_content.py`
- `lituk_questions_422.json` — question bank
