#  ScrapeX – Advanced Web Scraping Platform

A scalable, rule-based web scraping platform built in Python that supports automated data extraction from both static and dynamic websites, with job management, API integration, and multi-format data export.
<img width="1887" height="956" alt="image" src="https://github.com/user-attachments/assets/528fcf19-efc7-4e1c-979c-818bf46f79e1" />

<img width="1480" height="951" alt="image" src="https://github.com/user-attachments/assets/b6853f7b-1a7c-47bb-8fbf-acbb95a8c7c8" />
<img width="1480" height="951" alt="image" src="https://github.com/user-attachments/assets/b6853f7b-1a7c-47bb-8fbf-acbb95a8c7c8" />

---

##  Project Overview

ScrapeX is an advanced web scraping system designed to move beyond simple scripts and provide a modular, extensible scraping platform.

It allows users to:
- Define scraping rules using JSON
- Execute scraping jobs asynchronously
- Extract structured data from websites
- Handle pagination, retries, and failures
- Store results in a database
- Export data in multiple formats
- Interact via CLI or REST API

---

##  Key Features

-  Rule-based scraping system (JSON-driven)
-  Static scraping (Requests + BeautifulSoup)
-  Dynamic scraping (Playwright)
-  Pagination handling
-  Retry, backoff, throttling
-  Structured data extraction
-  SQLite storage
-  Export: JSON, CSV, XLSX
-  Async job execution
-  FastAPI backend
-  Logging and tracking

---

##  Installation

```bash
git clone <your-repo-url>
cd webscraper
pip install -r requirements.txt
```

For dynamic scraping:
```bash
python -m playwright install chromium
```

---

##  Usage

### Run Scraper
```bash
python scraper.py run-rule --rule advanced_rule.json
```

### Start API
```bash
python scraper.py api
```

Visit:
http://127.0.0.1:8000/docs

---

##  Example Rule

```json
{
  "site_name": "books",
  "start_urls": ["http://books.toscrape.com/catalogue/category/books/travel_2/index.html"],
  "scraper_type": "static"
}
```

---

##  Tech Stack

- Python
- FastAPI
- Requests
- BeautifulSoup
- Playwright
- SQLite

---
