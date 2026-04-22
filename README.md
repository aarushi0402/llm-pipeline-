# LLM Data Pipeline

A production-style Python pipeline that ingests text from files and URLs, analyzes each chunk using the **Groq LLM API**, and saves structured results to **JSON** and **Excel** along with a plain-text summary report.

---

## Features

- Accepts `.txt` and `.pdf` files + URLs in a single run
- Cleans and chunks text intelligently (respects LLM context limits)
- Extracts structured JSON from Groq: summary, entities, sentiment, key questions
- Robust retry logic with exponential backoff (rate limits, timeouts, server errors)
- Skips bad inputs gracefully — logs errors and continues
- Outputs: `results.json`, `results.xlsx`, `summary_report.txt`
- Fully modular — no LangChain or orchestration frameworks

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/llm-pipeline.git
cd llm-pipeline
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Groq API key
Get a free key at https://console.groq.com

**Linux/Mac:**
```bash
export GROQ_API_KEY="your_key_here"
```

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your_key_here"
```

---

## Usage

```bash
# Process a text file
python main.py --files article.txt

# Process a PDF
python main.py --files report.pdf

# Process URLs
python main.py --urls https://example.com https://another.com

# Process everything together
python main.py --files article.txt report.pdf --urls https://example.com
```

---

## Output

All outputs are saved in the `output/` folder with a timestamp:

| File | Description |
|------|-------------|
| `results_TIMESTAMP.json` | Full structured results per chunk |
| `results_TIMESTAMP.xlsx` | One row per chunk (summary, entities, sentiment, questions) |
| `summary_report_TIMESTAMP.txt` | Human-readable aggregated report |
| `pipeline.log` | Full log of the pipeline run |

---

## Project Structure

```
llm-pipeline/
├── main.py           # Entry point — orchestrates the pipeline
├── ingestion.py      # Load text from .txt/.pdf files and URLs
├── preprocessing.py  # Clean and chunk raw text
├── llm_client.py     # Groq API calls with retry + JSON parsing
├── storage.py        # Save results to JSON and Excel
├── report.py         # Generate plain-text summary report
├── requirements.txt
└── README.md
```

---

## Design Decisions

### Why Groq?
Groq offers extremely fast inference (often <1s per request), a generous free tier, and supports Llama 3 models which perform very well at structured JSON extraction tasks. It's ideal for a pipeline that needs to process many chunks quickly.

### Why no LangChain?
Direct API calls give full control over retries, error handling, and JSON parsing. LangChain abstracts too much away, making it harder to handle edge cases (malformed JSON, partial responses, rate limits) properly.

### Chunking Strategy
Text is split on paragraph boundaries first, then sentence boundaries if paragraphs are too large. This preserves semantic coherence rather than hard-cutting at character limits.

### Error Handling
- Network errors → retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
- Malformed JSON → regex-based extraction fallback, then structured default values
- Bad input files/URLs → logged and skipped, pipeline continues

---

## Tested With

- Wikipedia article (URL scraping)
- Multi-page PDF research paper
- Plain text news article
- URL returning a 404 (error handling verified)

---

## Known Limitations

- Very large PDFs (100+ pages) will generate many chunks and may hit rate limits
- Scanned PDFs (image-only) cannot be extracted without OCR
- Some heavily JavaScript-rendered pages may not scrape correctly
- Token counting is approximate (character-based), not exact
