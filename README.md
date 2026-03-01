# Pay Transparency Tool

RAG-powered assistant and pay gap analysis tool for EU Directive 2023/970 compliance.

## Stack

- **Backend**: FastAPI + Jinja2 + HTMX
- **RAG**: FastEmbed (MiniLM-L6-v2) + Qdrant (local) + BM25 Fusion Retrieval
- **LLM**: Groq API (Llama 3.3)
- **Analysis**: pandas + openpyxl (gender pay gap calculator)

## Setup

```bash
cp config.yaml.example config.yaml   # add your Groq API key
bash setup.sh                         # creates venv, installs deps, builds vectordb
```

## Usage

```bash
# Web interface
source .venv/bin/activate
uvicorn app:app --reload

# CLI
python main.py ask "Cosa dice l'art. 7 della Direttiva EU 2023/970?"
python main.py analyze --file data/sample.csv
```

## License

MIT
