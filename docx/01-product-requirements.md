# Life in the UK Platform - Product Requirements (Django)

## 1. Goal
Build a Django-based web platform for Life in the UK preparation with:
- Account and session validity tracking (30-day active window)
- Study plan and study content learning flow
- Practice engine with topic-based and mixed-topic modes
- Mock test engine following the official blueprint
- User behavior tracking and intelligence-style performance insights
- Dashboard with overall and topic-wise progress

## 2. Core Modules

### 2.1 Login and Account
- Registration fields (minimal): Name, Email, Password
- Login via email and password
- Account active for 30 days from registration (or activation date)
- Banner shown at login and dashboard with remaining active days
- Profile page with change password capability

Acceptance criteria:
- Remaining days shown as: `X days remaining`
- If expired, all user recode will be errised/removed and user cannot login.
- Password change requires old password validation

### 2.2 Study Plan
- Recreate study plan experience from source page in `web_back/Example Life in the UK Study Plan _ Official Life in the UK Learning Zone.mhtml`
- Build app-native layout (not iframe) with clear weekly/day milestones
- Mark steps as complete and show completion progress

Acceptance criteria:
- User sees a study plan timeline/checklist
- Completion percentage updates as tasks are completed
- Plan can be resumed from last completed step

### 2.3 Study
- Ingest topic pages from `web_back/1_1.mhtml` ... `web_back/5_8.mhtml`
- Group content by 5 topics
- Track per-user progress:
  - visited pages
  - completed pages
  - time spent
  - last viewed location/page

Acceptance criteria:
- User can navigate chapter pages sequentially
- Progress is visible per topic and overall
- Resume button opens latest unfinished page

### 2.4 Practice
- Import `lituk_questions_422.json` into normalized DB models
- Practice options:
  - random 10
  - random 20
  - random 30
  - all questions
  - all unanswered questions
- Scope options:
  - one topic
  - multiple topics
- Question flow:
  - one question at a time
  - next/previous navigation
  - explanation shown immediately after answering
  - final score at end

Progress/activity tracking:
- question attempts
- correctness
- response time
- explanation viewed
- per-topic mastery progress

Acceptance criteria:
- User can complete selected practice set and view score
- Unanswered filter only returns unseen/incorrect-unresolved questions (final rule to be chosen)
- Topic-level progress updates after each session

### 2.5 Mock Test
- 24 questions with fixed blueprint:
  - The values and principles of the UK: 1
  - What is the UK?: 1
  - A long and illustrious history: 8
  - A modern, thriving society: 7
  - The UK government, the law and your role: 7
- 45-minute timer
- Pass threshold: 18/24

Behavior tracking:
- per-question time engaged
- answer changes
- skipped vs answered
- question revisit counts
- final submission timing

Analytics outputs:
- score, pass/fail
- per-topic score
- weak-topic ranking
- pace metrics (fast/normal/slow)

Acceptance criteria:
- Auto-submit at timeout
- Full metrics saved for post-test analysis
- Mock test history available on dashboard

### 2.6 Dashboard
- Unified progress view:
  - study completion
  - practice performance
  - mock test performance
- Topic-wise progress and trends
- Insight cards and charts

Acceptance criteria:
- User sees overall readiness score
- User sees weakest topic and recommended next action
- Dashboard updates after each new activity

## 3. Design Principle
- Bold and simple UI
- Use Bootstrap 5 for speed and consistency
- Use Chart.js for graphs/charts
- Mobile-first responsive layout

## 4. Non-Functional Requirements
- Secure authentication and CSRF protection
- PostgreSQL-backed persistence
- Migration-safe schema
- Import scripts for JSON and MHTML content
- Basic audit trail for major user actions

## 5. Delivery Scope
### Phase 1 (MVP)
- Accounts, Study, Practice, Mock Test, Dashboard baseline

### Phase 2
- Advanced analytics and insight recommendations
- Learning streaks and nudges
- Admin analytics and content update tools
