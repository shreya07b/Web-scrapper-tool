from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from webscraper.models import ScrapedRecord


class ExportService:
    def __init__(self, export_dir: str = "exports") -> None:
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export(self, job_id: str, records: list[ScrapedRecord], formats: list[str]) -> list[str]:
        paths: list[str] = []
        rows = [record.extracted_json for record in records]
        for fmt in formats:
            if fmt == "json":
                path = self.export_dir / f"{job_id}.json"
                path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
                paths.append(str(path))
            elif fmt == "csv":
                path = self.export_dir / f"{job_id}.csv"
                self._write_csv(path, rows)
                paths.append(str(path))
            elif fmt == "xlsx":
                path = self.export_dir / f"{job_id}.xlsx"
                self._write_xlsx(path, rows)
                paths.append(str(path))
        return paths

    def _write_csv(self, path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _write_xlsx(self, path: Path, rows: list[dict]) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "scraped_data"
        if rows:
            headers = list(rows[0].keys())
            sheet.append(headers)
            for row in rows:
                sheet.append([row.get(header) for header in headers])
        workbook.save(path)
