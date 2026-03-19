import argparse
import json
from pathlib import Path

import uvicorn

from webscraper.job_manager import JobManager
from webscraper.models import JobCreateRequest, RuleDefinition
from webscraper.storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advanced web scraper platform CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    api_parser = subparsers.add_parser("api", help="Run the FastAPI server.")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)

    run_parser = subparsers.add_parser(
        "run-rule", help="Create and run a scraping job from a rule JSON file."
    )
    run_parser.add_argument("--rule", required=True, help="Path to rule JSON file.")
    run_parser.add_argument(
        "--db-path",
        default="scraper.db",
        help="SQLite database path. Defaults to scraper.db.",
    )
    return parser


def run_api(host: str, port: int) -> None:
    uvicorn.run("webscraper.api:app", host=host, port=port, reload=False)


async def run_rule(rule_path: str, db_path: str) -> None:
    storage = Storage(db_path)
    storage.initialize()
    manager = JobManager(storage)

    raw_rule = json.loads(Path(rule_path).read_text(encoding="utf-8"))
    rule = RuleDefinition.model_validate(raw_rule)
    rule_id = storage.create_rule(rule)

    request = JobCreateRequest(rule_id=rule_id, output_formats=["json", "csv", "xlsx"])
    job = await manager.create_job(request)
    print(f"Created job {job.job_id}")

    while True:
        status = manager.get_job_status(job.job_id)
        print(f"Job {job.job_id}: {status.status}")
        if status.status in {"success", "failed", "cancelled"}:
            print(f"Results: {len(manager.get_job_results(job.job_id))} record(s)")
            break
        await manager.sleep_briefly()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "api":
        run_api(args.host, args.port)
        return 0

    if args.command == "run-rule":
        import asyncio

        asyncio.run(run_rule(args.rule, args.db_path))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
