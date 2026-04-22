"""
storage.py — Save pipeline results to JSON and Excel
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(exist_ok=True)


def flatten_result(result: dict) -> dict:
    """Flatten nested JSON result into a single-level dict for Excel rows."""
    entities = result.get("entities", {})
    sentiment = result.get("sentiment", {})
    questions = result.get("key_questions", ["", "", ""])

    return {
        "source": result.get("source", ""),
        "chunk_index": result.get("chunk_index", 0),
        "chunk_preview": result.get("chunk_text", "")[:300],
        "summary": result.get("summary", ""),
        "people": ", ".join(entities.get("people", [])),
        "places": ", ".join(entities.get("places", [])),
        "organizations": ", ".join(entities.get("organizations", [])),
        "sentiment_label": sentiment.get("label", ""),
        "sentiment_confidence": round(float(sentiment.get("confidence", 0.0)), 2),
        "question_1": questions[0] if len(questions) > 0 else "",
        "question_2": questions[1] if len(questions) > 1 else "",
        "question_3": questions[2] if len(questions) > 2 else "",
    }


def save_results(results: list[dict]):
    ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Save JSON ──────────────────────────────────────────────────────────────
    json_path = OUTPUT_DIR / f"results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON saved → {json_path}")

    # ── Save Excel ─────────────────────────────────────────────────────────────
    flat_rows = [flatten_result(r) for r in results]
    df = pd.DataFrame(flat_rows)

    excel_path = OUTPUT_DIR / f"results_{timestamp}.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")

        # Auto-adjust column widths
        worksheet = writer.sheets["Results"]
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 4
            col_letter = worksheet.cell(row=1, column=col_idx).column_letter
            worksheet.column_dimensions[col_letter].width = min(max_len, 60)

    logger.info(f"Excel saved → {excel_path}")
