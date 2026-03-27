# NutriCoach AI Cloud Deployment Guide

This guide helps you deploy the current MVP to a cloud platform with:
- FastAPI app
- PostgreSQL database
- Twilio WhatsApp webhook

## 1. Prerequisites

- GitHub repo with this codebase
- Twilio account with WhatsApp Sandbox or approved WhatsApp sender
- OpenAI/Groq key (based on your model usage)
- FatSecret API credentials
- Cloud account: Railway or Render

## 2. Required Environment Variables

Set these in your cloud platform:

```env
# App
PYTHONUNBUFFERED=1

# Database
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# LLM / LangChain
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=nutricoach-ai

# Groq (if used in agents)
GROQ_API_KEY=

# Nutrition API
CLIENT_ID_FOOD=
CLIENT_SECRET_FOOD=
```

## 3. Start Command

Use this start command on cloud:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 4. Deploy on Railway (Recommended)

1. Create a new Railway project from your GitHub repo.
2. Add a PostgreSQL service in Railway.
3. Copy generated DB URL into `DATABASE_URL`.
4. Add all environment variables from section 2.
5. Set start command:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy.

## 5. Deploy on Render (Alternative)

1. Create a new Web Service from GitHub.
2. Runtime: Python.
3. Build command:
   `pip install -r requirements.txt`
4. Start command:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add a managed PostgreSQL instance and set `DATABASE_URL`.
6. Add all environment variables from section 2.
7. Deploy.

## 6. Run Migrations

After first deploy, run:

```bash
alembic upgrade head
```

If platform supports one-off shell/console, run it there.

## 7. Configure Twilio Webhook

In Twilio WhatsApp Sandbox/Number configuration:

- Webhook URL:
  `https://<your-domain>/webhook/whatsapp`
- Method: `POST`

## 8. Post-Deploy Smoke Test

1. Open:
   `https://<your-domain>/health`
2. Expect:
   `{"status":"ok"}`
3. Send a WhatsApp test message from a registered number.
4. Confirm:
   - message is routed
   - DB `meal_log` row is created
   - reply is sent back on WhatsApp

## 9. Production Notes

- Use managed Postgres backups.
- Keep API keys in platform secrets, not in code.
- Add request/error logging and alerting.
- Use one worker first, then scale after validating webhook behavior.
- Restart deployment after changing env vars.

## 10. Common Issues

- `Error 8: Invalid signature` (FatSecret):
  verify `CLIENT_ID_FOOD` and `CLIENT_SECRET_FOOD`, no spaces/quotes, system time sync.
- Twilio replies not arriving:
  check webhook URL path and Twilio logs.
- DB insert errors:
  verify `DATABASE_URL` and run migrations.

