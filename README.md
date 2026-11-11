# RecallSearch — Web Search Chat Agent

**A fast, source-aware chat agent with exactly one agent tool: web search.** It keeps a timestamped memory of what you asked and can bring relevant earlier questions back into the conversation.

> Built for the web-search agent challenge. The model is only given the hosted OpenAI `web_search` tool; conversation memory is ordinary application storage, not an additional agent tool.

## What it does

- Answers questions with the OpenAI Responses API.
- Uses web search when freshness or verification matters; skips it when it is unnecessary.
- Shows source links extracted from response citation annotations.
- Saves each user question and assistant answer to SQLite with a UTC timestamp.
- Recalls relevant prior questions and their timestamps on later turns.
- Shows a recent-question timeline and supports separate conversations / clearing the current conversation.
- Uses bounded history, low reasoning effort, and low search context to keep requests lean.

## Quick start

### 1. Requirements

- Python 3.10+
- An OpenAI API key with access to the Responses API and hosted web search

### 2. Install

```bash
git clone https://github.com/<your-username>/recallsearch-web-agent.git
cd recallsearch-web-agent
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. The default model is `gpt-6-astra`; set `OPENAI_MODEL` to another model available to your API project if needed.

### 4. Run

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit. Memory is stored in `data/recallsearch.sqlite3` by default. Change `MEMORY_DB_PATH` to use another local database file.

## Try these prompts

1. `What are the latest changes to the Python release schedule?`
2. `Remember that I'm comparing two cloud certifications. What did I ask about earlier?`
3. `What did I ask you about Python, and when did I ask it?`
4. `Explain the difference between a SQL join and a union.`

The first prompt should usually trigger web search. The last one may be answered without a search. Memory prompts are answered from the saved conversation only.

## Design

See [`design.md`](design.md) for architecture, request flow, memory design, accuracy controls, and production limitations. See [`PUBLISH.md`](PUBLISH.md) for steps to create and push the public GitHub repository.

## Tests

```bash
pytest -q
```

Tests cover timestamped persistence, session isolation, lexical recall, citation extraction, blank-prompt handling, and the invariant that the agent exposes only the web search tool.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | API authentication |
| `OPENAI_MODEL` | `gpt-6-astra` | Responses API model |
| `OPENAI_TIMEOUT_SECONDS` | `35` | API timeout |
| `MEMORY_DB_PATH` | `data/recallsearch.sqlite3` | SQLite memory database |
| `APP_TIMEZONE` | `Asia/Kolkata` | Timezone for timeline display |

## Privacy and deployment notes

This is a local, single-user starter. The SQLite file contains conversation text and timestamps and is not encrypted. Do not deploy it as a public multi-user app without authentication, per-user database isolation, retention controls, secure secrets management, and encrypted storage. Never commit `.env` or the database file.

## API references

- [OpenAI web search guide](https://developers.openai.com/api/docs/guides/tools-web-search)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## License

MIT. See [`LICENSE`](LICENSE).
