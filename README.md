# AI News Auto-Blogger & Email Automation using Python + GROQ LLM

Production-ready daily automation pipeline that fetches AI news, summarizes with GROQ, generates a blog, formats HTML email, sends automatically, and stores analytics.

## 1) System Architecture

### End-to-end flow (matches required logic)

```
Trigger (Schedule/Cron)
        |
        v
News API (SerpAPI Google News)
        |
        v
Filter AI News (keyword scoring + categorization)
        |
        v
LLM (GROQ OpenAI-compatible Chat Completions)
        |
        v
Blog Generator (Markdown + HTML)
        |
        v
Email Formatter (template rendering)
        |
        v
Gmail / SMTP Sender
```

### Python module mapping

- `scheduler.py`: trigger layer (daily schedule)
- `fetch_news.py`: SerpAPI integration
- `filter_news.py`: AI filtering + analytics
- `llm_service.py`: GROQ summarization + blog generation
- `blog_generator.py`: Markdown/HTML blog artifact creation
- `email_formatter.py`: HTML email layout and merge
- `email_sender.py`: SMTP delivery
- `main.py`: orchestrator connecting all modules in order

## 2) Tech Stack

- Python 3.10+
- `pandas` (data processing + CSV persistence)
- `requests` (API calls)
- GROQ API (OpenAI-compatible endpoint)
- SMTP/Gmail (email)
- `schedule` (daily automation)

## 3) Project Structure

```
project/
│
├── main.py
├── scheduler.py
├── fetch_news.py
├── filter_news.py
├── llm_service.py
├── blog_generator.py
├── email_formatter.py
├── email_sender.py
├── data/
│   └── news.csv
├── templates/
│   └── email_template.html
├── prompts/
│   └── prompts.txt
├── config.py
├── requirements.txt
└── README.md
```

## 4) Environment Setup

Create a `.env` file in the project root:

```env
# API keys
SERPAPI_API_KEY=your_serpapi_key
GROQ_API_KEY=your_groq_api_key

# GROQ model config
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1

# SMTP / Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_SUBJECT=Daily AI News Brief

# News fetch config
NEWS_QUERY=artificial intelligence OR generative AI OR large language model OR machine learning
NEWS_RESULTS_LIMIT=20
NEWS_COUNTRY=us
NEWS_LANGUAGE=en

# Automation config
SCHEDULE_TIME_24H=09:00
REQUEST_TIMEOUT_SECONDS=30
```

Gmail note:
- Use a Gmail App Password (not your regular account password) when 2FA is enabled.

## 5) Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## 6) Run Modes

### A) Run once (manual pipeline)

```bash
python main.py
```

Outputs generated:
- `data/news.csv` (history + deduplicated links)
- `data/latest_summary.json`
- `data/latest_blog.md`
- `data/latest_blog.html`

### B) Run daily with Python schedule

```bash
python scheduler.py
```

Runs every day at `SCHEDULE_TIME_24H`.

## 7) Automation Alternatives

### Cron (Linux/macOS)

Run daily at 09:00:

```cron
0 9 * * * /path/to/venv/bin/python /path/to/project/main.py >> /path/to/project/data/cron.log 2>&1
```

### Windows Task Scheduler

- Program/script: `C:\path\to\venv\Scripts\python.exe`
- Add arguments: `C:\path\to\project\main.py`
- Trigger: Daily, choose your time

## 8) Data Analytics Included

Implemented in `filter_news.py`:
- Article count
- Top keywords (frequency-based)
- Source distribution
- Category distribution (heuristic mapping)

These analytics are inserted into the email report under **Data Snapshot**.

## 9) Prompt Engineering

`prompts/prompts.txt` includes:
- `NEWS_SUMMARIZATION_PROMPT` (strict JSON schema output)
- `BLOG_GENERATION_PROMPT` (SEO-ready, heading-structured markdown article)

## 10) Reliability & Production Notes

- Environment-variable validation at startup (`config.py`)
- Timeout-controlled API calls
- Link-level deduplication before storage
- Structured module boundaries for maintainability
- Scheduler has protected job execution with exception logging

## 11) Quick Verification Checklist

- [ ] `.env` values configured
- [ ] `python main.py` sends email successfully
- [ ] `data/news.csv` receives rows
- [ ] `data/latest_blog.md` and `data/latest_blog.html` generated
- [ ] `python scheduler.py` runs and idles correctly for daily trigger
