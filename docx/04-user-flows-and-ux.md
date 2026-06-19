# User Flows and UX Blueprint

## 1. UX Direction
- Bold and simple visual language
- Bootstrap 5 base + custom color tokens + large touch targets
- Mobile-first layout with responsive cards/charts

## 2. Main Navigation
- Dashboard
- Study Plan
- Study
- Practice
- Mock Test
- Profile

## 3. Flow: Register and Login
```mermaid
flowchart TD
  A[Open App] --> B{Has account?}
  B -- No --> C[Register: Name, Email, Password]
  C --> D[Create user with active_until = now + 30 days]
  D --> E[Login]
  B -- Yes --> E[Login]
  E --> F[Show remaining days banner]
  F --> G[Dashboard]
```

## 4. Flow: Study
```mermaid
flowchart TD
  A[Study page list] --> B[Open chapter page]
  B --> C[Track visit and start time]
  C --> D[Next or previous chapter]
  D --> E[Update time spent and status]
  E --> F[Topic completion percentage]
```

## 5. Flow: Practice Session
```mermaid
flowchart TD
  A[Choose topics and mode] --> B[Generate question set]
  B --> C[Show one question at a time]
  C --> D[User answers]
  D --> E[Immediately show explanation]
  E --> F{Next or previous?}
  F --> C
  F --> G[Finish session]
  G --> H[Show score + per-topic metrics]
  H --> I[Save progress snapshots]
```

## 6. Flow: Mock Test Session
```mermaid
flowchart TD
  A[Start mock test] --> B[Generate 24Q blueprint]
  B --> C[Start 45 min timer]
  C --> D[Capture per-question engagement]
  D --> E[Submit or auto-submit]
  E --> F[Score and pass/fail]
  F --> G[Behavior analytics + insights]
  G --> H[Persist for dashboard]
```

## 7. Dashboard Experience
- Top cards:
  - Active days remaining
  - Overall readiness score
  - Last mock score
  - Practice streak
- Charts:
  - Topic-wise accuracy (bar chart)
  - Study completion by topic (horizontal bars)
  - Practice and mock trend over time (line chart)
- Insights:
  - weakest topic
  - slowest topic by response time
  - recommendation list (next 3 actions)

## 8. UX Enhancements to include in build
- Sticky action area for mobile in practice/mock
- Unanswered question indicator
- Jump-to-question navigator
- Session resume where safe
- Accessible contrast and keyboard navigation
