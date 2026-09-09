# Innovaction in Action

Multilingual AI assistant that turns an innovation objective into an executable innovation dynamic and a downloadable PDF, grounded in Alberto Muñoz's **Innovaction** knowledge base.

## Languages
English, Spanish, French, Chinese, Japanese, Russian, Korean, German, Arabic and Hebrew.

## Architecture

```text
User browser
   |
   v
Vercel / Next.js  ---> /api/generate proxy
                         |
                         v
                 Spark FastAPI API
                         |
                Retrieval over corpus
                         |
               Local OpenAI-compatible LLM
                         |
                 structured JSON plan
   <---------------------+
   |
   +--> browser PDF export (MVP)
   +--> server branded PDF (production option)
```

The first prototype works even before Spark is connected: the Vercel route returns a deterministic demo dynamic. When `SPARK_INNOVACTION_API_URL` is configured, the frontend calls Spark; if Spark is temporarily unavailable, it falls back to the demo.

## Knowledge model
The initial method catalog is based on the book sections covering creative processes, Innovation Games, Design Thinking/Canvas, Customer Journey, TRL, POC/MVP, technology surveillance/IP, triple helix, ISO 5600x, innovation metrics, sustainability and Industry 4.0. The backend retrieves relevant chunks and asks the local LLM to compose a fit-for-purpose dynamic rather than returning a fixed template.

## Local frontend
```bash
npm install
npm run dev
```

## Spark backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ingest_pdf.py /path/to/InnovactionMunoz2022.pdf ../data/chunks.json
uvicorn main:app --host 0.0.0.0 --port 8012
```

Recommended production variables are in `.env.example`.

## Suggested production URL layout
- `https://innovaction.albertomunoz.ai` -> Vercel frontend
- `https://innovaction-api.albertomunoz.ai` -> Cloudflare Tunnel -> Spark FastAPI on port 8012

## Drive corpus
For the Drive folder, use a synchronization process on Spark that downloads/updates supported files into a local corpus, extracts text and metadata, chunks them, and rebuilds the index. Keep provenance (`file`, `page/slide`, `updated_at`) with every chunk so generated dynamics can cite their source. Do not send the full Drive corpus to the LLM; retrieve only the most relevant chunks.

## Next production hardening
1. Add embeddings + hybrid BM25/vector retrieval.
2. Add citations into each activity and final PDF.
3. Add server-side branded PDF for full Unicode font support in all languages.
4. Add session history and saved innovation projects.
5. Add an evaluator/critic second LLM pass for feasibility, novelty, value and execution quality.
6. Add optional web/patent/market research agents as explicit tools, clearly separated from book-derived evidence.
