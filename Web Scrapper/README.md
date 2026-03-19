# Advanced Web Scraper Platform

This project is now structured as a scraping engine platform rather than a single script. It supports rule-based extraction, static and dynamic scraping modes, async job execution, SQLite-backed job/result storage, REST APIs, and JSON/CSV/XLSX exports.

## Architecture

```text
User / Admin
    |
    v
FastAPI API
    |
    v
Async Job Manager
    |
    v
Scraper Engine
    |---- Static scraper (requests + BeautifulSoup)
    |---- Dynamic scraper (Playwright)
    |---- Parser / extractor (CSS, XPath, regex)
    |---- Reliability layer (retries, rate limiting, proxy rotation hooks)
    |
    v
Storage + Export
    |---- SQLite metadata + results
    |---- JSON / CSV / XLSX exports
    |
    v
Logs + Job Status
```

## Main Files

- `scraper.py`: CLI entrypoint for starting the API or running a rule directly
- `webscraper/api.py`: FastAPI endpoints for rules, jobs, results, and logs
- `webscraper/job_manager.py`: async job orchestration
- `webscraper/engine.py`: static/dynamic scraper engine
- `webscraper/storage.py`: SQLite storage layer
- `webscraper/exporters.py`: JSON, CSV, and Excel export support
- `webscraper/extractors.py`: CSS, XPath, and regex field extraction
- `webscraper/pagination.py`: pagination strategies
- `advanced_rule.json`: example multi-page scraping rule

## Installation

```bash
python -m pip install -r requirements.txt
```

Optional for dynamic sites:

```bash
python -m playwright install chromium
```

## Run The API

```bash
python scraper.py api --host 127.0.0.1 --port 8000
```

Dashboard UI will be available at `http://127.0.0.1:8000/dashboard`.

Swagger UI will be available at `http://127.0.0.1:8000/docs`.

## Run A Job From A Rule File

```bash
python scraper.py run-rule --rule advanced_rule.json
```

This will:

- register the rule
- create an async scraping job
- store job data in `scraper.db`
- export results to the `exports/` folder

## API Endpoints

- `POST /rules/create`
- `GET /sites/supported`
- `POST /jobs/create`
- `POST /jobs/run/{job_id}`
- `GET /jobs/status/{job_id}`
- `GET /jobs/results/{job_id}`
- `GET /jobs/logs/{job_id}`

## Rule Format

Example:

```json
{
  "site_name": "books_demo",
  "rule": {
    "site_name": "books_demo",
    "start_urls": ["https://example.com/products"],
    "scraper_type": "static",
    "item_selector": ".product-card",
    "pagination": {
      "type": "next_button",
      "selector": ".next-page a",
      "max_pages": 5
    },
    "anti_block": {
      "max_retries": 3,
      "backoff_seconds": 1.0,
      "rate_limit_per_second": 1.0,
      "proxy_urls": [],
      "rotate_user_agent": true,
      "timeout_seconds": 20
    },
    "fields": [
      {
        "name": "title",
        "selector": ".product-title",
        "selector_type": "css",
        "required": true
      },
      {
        "name": "link",
        "selector": ".product-link",
        "selector_type": "css",
        "attr": "href"
      }
    ]
  }
}
```

## Features Included

- static scraping with `requests`
- dynamic scraping hook with Playwright
- async job execution with background tasks
- pagination handling for `next_button` and `page_param`
- retry with backoff
- rate limiting
- rotating user agents
- proxy list support
- rule-based extraction
- CSS, XPath, and regex extraction modes
- SQLite-backed jobs, results, rules, and logs
- export to JSON, CSV, and XLSX

## Notes

- This version uses SQLite to keep local setup simple. PostgreSQL or MongoDB can be added behind the same storage boundary later.
- The dynamic scraper is optional and requires Playwright plus browser binaries.
- Scheduling, distributed workers, auth flows, and a full frontend dashboard are the next logical upgrades if you want to push this toward production.
