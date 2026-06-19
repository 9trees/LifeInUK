# Implementation Roadmap (Pre-Deployment)

## 1. Milestone Plan

### Implementation Status Update (2026-06-19) — Django build

The implementation now follows the planned Django architecture under `django_app/`.
The earlier static HTML/JS files (index.html, app.js, styles.css) were a prototype
and are superseded by the Django app.

Django apps and status:
- accounts: custom email user, register/login/logout, profile + password change,
  30-day active window via middleware + banner context processor — DONE
- content: Topic, StudyPage (JSON blocks), StudyPlanItem + import commands — DONE
- study: rich study reader (headings, bullets, images, tables), sequential nav,
  per-user progress (visits, status, completion, time) — DONE
- practice: Question/AnswerOption/PracticeSession/PracticeResponse, topic + mode
  selection (random 10/20/30/all/unanswered), one-at-a-time flow with explanation,
  topic scoring — DONE
- mocktest: 24-question blueprint generator, 45-min timer + auto-submit, behavior
  events, pass mark 18, topic results — DONE
- analytics: Bootstrap 5 + Chart.js dashboard (topic accuracy, mock trend,
  weakest topic) — DONE

Data imported: 5 topics, 27 study pages (with 47 images), 29 plan items, 422 questions.
Verified end-to-end in the browser (register → study image page → practice
explanation → mock 24Q timer). Default DB is SQLite; set DATABASE_URL for Postgres.

### (Legacy prototype) Implementation Status Update (2026-06-19)
- Milestone A started in current codebase (single-page implementation baseline).
- Completed now:
  - Registration, login, logout flows
  - 30-day active-window banner and expiry cleanup behavior
  - Profile page with old-password validation and password change flow
  - Dashboard summary cards for active days and mock history
  - Existing mock test module integrated into app navigation shell
- Milestone B started in current codebase.
- Completed now (Milestone B slice):
  - Authenticated live-site scraper (scrape_study_content.py) capturing ordered
    content blocks (headings, paragraphs, bullets, images, tables) for 27 pages
  - Local image assets downloaded to assets/study/ (47 images) for offline use
  - Study plan extraction and checklist dataset generation
  - Study view with topic filtering, page list, and per-page status
  - Study reader rebuilt to match the official site reading style (serif
    headings, figures with captions, tables) with previous/next + resume
  - Study progress tracking per user: visits, completion, time spent, last viewed
- Next in sequence:
  - Milestone C practice engine implementation

### Milestone A - Foundation (Week 1)
- Initialize Django project and apps
- Configure PostgreSQL and environment settings
- Implement custom user model and auth flows
- Implement 30-day active window and banner logic
- Create profile and change-password flow

Exit criteria:
- User can register/login/logout/change password
- Remaining-days banner works

### Milestone B - Content and Study (Week 2)
- Build topic and study content models
- Create MHTML import command for study pages
- Implement study plan page and progress model
- Implement study reader with sequential navigation

Exit criteria:
- All study pages imported and browsable
- Study progress saved and visible

### Milestone C - Practice Engine (Week 3)
- Import 422-question bank into models
- Practice setup screen (topics + mode)
- Question-by-question practice UI with explanation after answer
- Session scoring and persistence
- Practice analytics by topic

Exit criteria:
- Practice modes work (10/20/30/all/unanswered)
- Session and topic metrics tracked

### Milestone D - Mock Test Engine (Week 4)
- Blueprint-based mock generator
- 45-minute timer and auto-submit
- User behavior event tracking per question
- Mock result and insights page

Exit criteria:
- Full mock lifecycle with tracking and score
- Topic and behavior metrics available

### Milestone E - Dashboard and Intelligence (Week 5)
- Dashboard cards + charts
- Topic-wise and overall progress summaries
- Insight generation rules and recommendations

Exit criteria:
- Unified dashboard reflects study/practice/mock
- Insight cards generated per user

### Milestone F - QA and Launch Readiness (Week 6)
- Integration testing
- Data validation checks
- Performance pass and security checks
- Deployment rehearsal and rollback verification

Exit criteria:
- UAT sign-off
- Production-ready deployment package

## 2. Backlog Priorities
- P0: auth, question import, practice engine, mock engine, tracking
- P1: study parser fidelity, dashboard visuals, insights
- P2: richer personalization, notifications, advanced analytics

## 3. Testing Strategy
- Unit tests: model rules, selection logic, scoring logic
- Integration tests: practice/mock session lifecycle
- UI tests: key flows for register, practice, mock, dashboard
- Data tests: import consistency for MHTML and JSON

## 4. Risks and Mitigations
- MHTML parsing inconsistency:
  - Mitigation: source parser abstraction with manual override support
- Tracking volume growth:
  - Mitigation: summary tables + periodic aggregation jobs
- Scope expansion:
  - Mitigation: strict milestone exits and release cut lines
