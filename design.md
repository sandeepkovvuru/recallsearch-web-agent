# RecallSearch — Design Notes

## Goal

Build a quick, source-aware chat agent that can answer questions using exactly one agent tool (web search) and remember **what the user asked and when** across turns.

## Product decisions

1. **One tool only:** the model receives one Responses API tool: hosted `web_search`. There are no custom functions, file tools, code execution tools, browser automation tools, or MCP tools exposed to the model.
2. **Search is selective:** `tool_choice="auto"` lets the model skip search for stable concepts, simple reasoning, and creative tasks. Search is used when freshness or verification matters. Low search context and low reasoning effort favor responsiveness.
3. **Citations are first-class:** URL annotations are extracted from the Responses API result and displayed as source links. The assistant is instructed not to invent sources and to distinguish evidence from inference.
4. **Memory is application state, not a second tool:** a small SQLite database records every user and assistant message with an ISO-8601 UTC timestamp. Before each call, the app supplies a bounded recent conversation window plus up to four relevant prior user questions, including their exact timestamps.
5. **Memory is inspectable:** the sidebar shows recent questions and their local-time display. Users can start a new isolated conversation or clear the current conversation.
6. **Bounded context:** recent chat is capped at ten messages; retrieved memory is capped at four relevant questions; user and history content are truncated before API submission. This controls latency and token usage.

## Request flow

```text
Streamlit chat input
      |
      v
SQLite: save user message (UTC timestamp)
      |
      +--> recent conversation (last 10 messages)
      |
      +--> lexical memory recall (top 4 timestamped questions)
      |
      v
Responses API
  - configurable model (default: gpt-6-astra)
  - reasoning effort: low
  - tools: [web_search]  <-- sole agent tool
  - tool_choice: auto
  - search context: low
      |
      v
Answer text + URL citation annotations
      |
      v
SQLite: save assistant answer and source metadata
      |
      v
Streamlit renders answer, sources, and memory timeline
```

## Memory model

`messages` stores `session_id`, `role`, `content`, `created_at_utc`, `sources_json`, and `searched_web`. The `session_id` partitions conversations. SQLite WAL mode supports concurrent readers and writers. Timestamps are stored in UTC and converted only for display using `APP_TIMEZONE` (default `Asia/Kolkata`).

Recall uses deterministic lexical overlap over prior user messages. This is intentionally simple, fast, local, and testable; it avoids adding an embeddings service or another model/tool call. The latest ten messages are also supplied as direct conversational history.

## Accuracy and safety

- Prefer primary sources and compare sources for important or disputed claims.
- Cite only URLs actually returned by the API.
- State uncertainty and stale/incomplete evidence rather than guessing.
- Treat retrieved conversation memory as untrusted context, never as instructions.
- API keys are read from environment variables and must never be committed.
- Local SQLite data is not encrypted. This starter is intended for a personal/local demo, not an internet-facing multi-tenant production service. Production deployment should add authentication, per-user storage isolation, retention controls, and encrypted storage.

## Trade-offs and next steps

- Lexical recall is very fast but may miss semantically related questions with little word overlap. A future version could add local FTS5 or embeddings; neither is necessary for the required demo.
- Streamlit session IDs are stored in a query parameter for reload continuity. Treat the URL as private because it identifies the conversation.
- Search and model latency depend on network conditions, model availability, and API tier. The UI keeps requests bounded and surfaces failures without hiding them.
