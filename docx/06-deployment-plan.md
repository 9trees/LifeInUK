# Deployment Plan and Environment Strategy

## 1. Environment Topology
- Local: Django dev + SQLite/Postgres (developer choice)
- Staging: Django + PostgreSQL + Redis + static assets
- Production: Django + PostgreSQL + Redis + HTTPS + monitoring

## 2. Build and Release
- Use environment variables for secrets/config
- Run migrations in CI/CD before app switch
- Collect static files during release
- Health check endpoint for rollout validation

## 3. Security Baseline
- HTTPS only in production
- Secure cookies and CSRF
- Strong password validation
- Rate limits on login attempts
- Basic audit logs for auth and test submission

## 4. Data Migration and Initialization
- Step 1: apply schema migrations
- Step 2: import topics and study plan
- Step 3: import study pages from MHTML files
- Step 4: import questions from JSON bank
- Step 5: run verification scripts

## 5. Observability
- App logs (structured)
- Error tracking
- DB slow query monitoring
- Daily job: analytics summary compaction

## 6. Rollback Strategy
- Keep previous app image/build available
- Backup DB before major migrations
- Roll back app first; roll back DB only if required and safe

## 7. Launch Checklist
- Auth flows tested end-to-end
- Study content rendering validated against source files
- Practice and mock scoring validated
- Dashboard charts accurate
- Expired-user behavior confirmed

## 8. Post-Launch Next Steps
- Add adaptive recommendations based on weak topics
- Add reminder notifications for daily study goals
- Introduce admin console for content updates
