# Security (Minimum)

## Auth
- Use JWT or API key for demo.
- Separate admin endpoints (optional) with stricter key.

## Secrets
- DB password / JWT secret stored in Secret Manager.
- Never hardcode secrets in repo.

## Data protection (demo scope)
- Avoid storing PII beyond userId.
- Log redaction: do not log full answers payload in production (demo can log minimal).
