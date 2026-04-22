"""
report.py — Generate a plain-text summary report across all results
"""

import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


def generate_report(results: list[dict], skipped: list[dict]):
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"summary_report_{timestamp}.txt"

    total = len(results)
    sources = list(dict.fromkeys(r["source"] for r in results))

    # Sentiment breakdown
    sentiments = [r.get("sentiment", {}).get("label", "unknown") for r in results]
    sentiment_counts = Counter(sentiments)

    # Collect all entities
    all_people = []
    all_places = []
    all_orgs = []
    for r in results:
        e = r.get("entities", {})
        all_people.extend(e.get("people", []))
        all_places.extend(e.get("places", []))
        all_orgs.extend(e.get("organizations", []))

    top_people = [name for name, _ in Counter(all_people).most_common(10)]
    top_places = [name for name, _ in Counter(all_places).most_common(10)]
    top_orgs = [name for name, _ in Counter(all_orgs).most_common(10)]

    # Avg sentiment confidence
    confidences = [
        float(r.get("sentiment", {}).get("confidence", 0))
        for r in results
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    lines = [
        "=" * 70,
        "          LLM DATA PIPELINE — SUMMARY REPORT",
        f"          Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
        "OVERVIEW",
        "-" * 40,
        f"  Total chunks analyzed   : {total}",
        f"  Sources processed       : {len(sources)}",
        f"  Chunks skipped          : {len(skipped)}",
        "",
        "SOURCES PROCESSED",
        "-" * 40,
    ]
    for src in sources:
        src_results = [r for r in results if r["source"] == src]
        lines.append(f"  • {src} ({len(src_results)} chunk(s))")

    lines += [
        "",
        "SENTIMENT BREAKDOWN",
        "-" * 40,
        f"  Positive  : {sentiment_counts.get('positive', 0)} chunk(s)",
        f"  Neutral   : {sentiment_counts.get('neutral', 0)} chunk(s)",
        f"  Negative  : {sentiment_counts.get('negative', 0)} chunk(s)",
        f"  Avg confidence : {avg_confidence:.0%}",
        "",
        "TOP ENTITIES MENTIONED",
        "-" * 40,
        f"  People        : {', '.join(top_people) if top_people else 'None found'}",
        f"  Places        : {', '.join(top_places) if top_places else 'None found'}",
        f"  Organizations : {', '.join(top_orgs) if top_orgs else 'None found'}",
        "",
        "CHUNK SUMMARIES",
        "-" * 40,
    ]

    for r in results:
        lines.append(f"\n  [{r['source']} — Chunk {r['chunk_index']+1}]")
        lines.append(f"  Summary   : {r.get('summary', 'N/A')}")
        lines.append(f"  Sentiment : {r.get('sentiment', {}).get('label', 'N/A')} "
                     f"({r.get('sentiment', {}).get('confidence', 0):.0%} confidence)")
        qs = r.get("key_questions", [])
        for qi, q in enumerate(qs, 1):
            lines.append(f"  Q{qi}: {q}")

    if skipped:
        lines += [
            "",
            "SKIPPED INPUTS",
            "-" * 40,
        ]
        for s in skipped:
            lines.append(f"  • Source: {s['source']} | Chunk: {s['chunk']} | Reason: {s['reason']}")

    lines += [
        "",
        "=" * 70,
        "END OF REPORT",
        "=" * 70,
    ]

    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    logger.info(f"Summary report saved → {report_path}")
    print("\n" + report_text)
