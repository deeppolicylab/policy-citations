#!/usr/bin/env python3
"""Build the dashboard data bundle from policy-impact-export.csv."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV =  "policy-impact-export.csv"
DEFAULT_OUTPUT =  "dashboard-data.js"

FIELD_MAP = {
    "mention_type": "Type",
    "document_id": "Policy Document ID",
    "title": "Title",
    "translated_title": "Translated title",
    "org": "Source title",
    "country": "Source country",
    "source_type": "Source type",
    "source_subtype": "Source sub-type",
    "published_on": "Published on",
    "paper": "Cited research titles",
    "doi": "Cited research DOIs",
    "topics": "Topics",
    "doc_url": "Document URL",
    "text": "Text",
}


def clean(value: str | None) -> str:
    return (value or "").strip().replace("\ufeff", "")


def normalize_source_type(value: str) -> str:
    value = clean(value).lower()
    return value or "other"


def parse_date(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    match = re.search(r"\d{4}", value)
    return value if not match else value


def year_from_date(value: str) -> str:
    match = re.search(r"\d{4}", value or "")
    return match.group(0) if match else ""


def split_topics(value: str) -> list[str]:
    parts = re.split(r"\s*[，,;|]\s*", clean(value))
    return [part.strip() for part in parts if part.strip()]


def split_cited_pair(title_value: str, doi_value: str) -> list[tuple[str, str]]:
    titles = [clean(title_value)]
    dois = [clean(doi_value)]

    if "，" in title_value:
        titles = split_topics(title_value)
    if "，" in doi_value:
        dois = split_topics(doi_value)

    pairs = []
    for index, title in enumerate(titles):
        doi = dois[index] if index < len(dois) else (dois[0] if len(dois) == 1 else "")
        if title:
            pairs.append((title, doi))
    return pairs


def sort_count_rows(counter: Counter, key_name: str, count_name: str) -> list[dict]:
    return [
        {key_name: key, count_name: count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))
    ]


def build_payload(csv_path: Path) -> dict:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    normalized = []
    paper_counts: Counter[str] = Counter()
    paper_dois: dict[str, str] = {}
    topic_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    mention_counts: Counter[str] = Counter()
    timeline_counts: Counter[str] = Counter()
    orgs: dict[str, dict] = {}

    for row in rows:
        item = {name: clean(row.get(source)) for name, source in FIELD_MAP.items()}
        item["source_type"] = normalize_source_type(item["source_type"])
        item["published_on"] = parse_date(item["published_on"])
        normalized.append(item)

        org = item["org"] or "Unknown"
        country = item["country"] or "Unknown"
        source_type = item["source_type"]
        published_on = item["published_on"]

        country_counts[country] += 1
        type_counts[source_type] += 1
        mention_counts[item["mention_type"] or "Unknown"] += 1

        year = year_from_date(published_on)
        if year:
            timeline_counts[year] += 1

        cited_pairs = split_cited_pair(item["paper"], item["doi"])
        for paper, doi in cited_pairs:
            paper_counts[paper] += 1
            if doi and paper not in paper_dois:
                paper_dois[paper] = doi

        for topic in split_topics(item["topics"]):
            topic_counts[topic] += 1

        if org not in orgs:
            orgs[org] = {
                "org": org,
                "country": country,
                "source_type": source_type,
                "citations": 0,
                "latest": published_on,
                "doc_url": item["doc_url"],
            }
        orgs[org]["citations"] += 1
        if published_on and published_on > (orgs[org]["latest"] or ""):
            orgs[org]["latest"] = published_on
            orgs[org]["doc_url"] = item["doc_url"]

    top_papers = [
        {"paper": paper, "citations": count, "doi": paper_dois.get(paper, "")}
        for paper, count in sorted(paper_counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]

    org_rows = sorted(orgs.values(), key=lambda item: (-item["citations"], item["org"].lower()))
    timeline = [
        {"year": year, "citations": timeline_counts[year]}
        for year in sorted(timeline_counts)
    ]

    return {
        "summary": {
            "total": len(normalized),
            "orgs": len(orgs),
            "countries": len(country_counts),
            "papers": len(paper_counts),
        },
        "top_papers": top_papers,
        "orgs": org_rows,
        "topics": sort_count_rows(topic_counts, "topic", "count")[:40],
        "timeline": timeline,
        "countries": sort_count_rows(country_counts, "country", "citations"),
        "types": sort_count_rows(type_counts, "source_type", "citations"),
        "mention_types": sort_count_rows(mention_counts, "type", "count"),
    }


def write_js(output_path: Path, payload: dict) -> None:
    json_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "// Automatically generated by scripts/build-data.py. Do not edit directly.\n"
        f"window.POLICY_CITATION_DATA = {json_payload};\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to policy-impact-export.csv")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Path for generated dashboard-data.js")
    args = parser.parse_args()

    payload = build_payload(args.csv)
    write_js(args.out, payload)
    print(f"Wrote {args.out} from {args.csv}")
    print(
        "Summary: "
        f"{payload['summary']['total']} mentions, "
        f"{payload['summary']['orgs']} organizations, "
        f"{payload['summary']['countries']} countries/IGOs, "
        f"{payload['summary']['papers']} papers"
    )


if __name__ == "__main__":
    main()
