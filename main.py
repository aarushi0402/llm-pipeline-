"""
LLM Data Pipeline - Main Entry Point
Usage: python main.py --files file1.txt file2.pdf --urls https://example.com
"""

import argparse
import logging
import sys
from pathlib import Path

from ingestion import load_file, load_url
from preprocessing import preprocess_and_chunk
from llm_client import analyze_chunk
from storage import save_results
from report import generate_report

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="LLM Data Pipeline")
    parser.add_argument("--files", nargs="*", default=[], help="Path(s) to .txt or .pdf files")
    parser.add_argument("--urls", nargs="*", default=[], help="URL(s) to scrape")
    return parser.parse_args()


def run_pipeline(files: list, urls: list):
    all_results = []
    skipped = []

    inputs = [("file", f) for f in files] + [("url", u) for u in urls]

    if not inputs:
        logger.error("No inputs provided. Use --files and/or --urls.")
        sys.exit(1)

    logger.info(f"Starting pipeline with {len(inputs)} input(s).")

    for input_type, source in inputs:
        logger.info(f"Processing {input_type}: {source}")
        try:
            # 1. Ingest
            if input_type == "file":
                raw_text = load_file(source)
            else:
                raw_text = load_url(source)

            # 2. Preprocess + chunk
            chunks = preprocess_and_chunk(raw_text, source=source)
            logger.info(f"  -> {len(chunks)} chunk(s) created from '{source}'")

            # 3. Analyze each chunk via LLM
            for i, chunk in enumerate(chunks):
                logger.info(f"  -> Analyzing chunk {i+1}/{len(chunks)} ...")
                result = analyze_chunk(chunk, source=source, chunk_index=i)
                if result:
                    all_results.append(result)
                else:
                    logger.warning(f"  -> Chunk {i+1} from '{source}' returned no result, skipping.")
                    skipped.append({"source": source, "chunk": i, "reason": "LLM returned no result"})

        except Exception as e:
            logger.error(f"Failed to process '{source}': {e}")
            skipped.append({"source": source, "chunk": "all", "reason": str(e)})
            continue

    if not all_results:
        logger.error("No results were produced. Exiting.")
        sys.exit(1)

    # 4. Save results
    logger.info("Saving results...")
    save_results(all_results)

    # 5. Generate report
    logger.info("Generating summary report...")
    generate_report(all_results, skipped)

    logger.info("✅ Pipeline complete! Check output/ folder for results.")


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(files=args.files, urls=args.urls)
