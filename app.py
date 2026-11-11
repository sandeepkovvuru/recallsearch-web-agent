"""Streamlit UI for RecallSearch."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st
from dotenv import load_dotenv

from agent import WebSearchAgent
from memory import SQLiteMemory

load_dotenv()
st.set_page_config(page_title="RecallSearch", page_icon="🔎", layout="wide")


def get_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Kolkata"))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def display_time(utc_timestamp: str) -> str:
    try:
        value = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
        return value.astimezone(get_timezone()).strftime("%d %b %Y, %I:%M:%S %p %Z")
    except (ValueError, TypeError):
        return utc_timestamp


@st.cache_resource
def get_memory(db_path: str) -> SQLiteMemory:
    return SQLiteMemory(db_path)


st.markdown(
    """
    <style>
    .block-container {max-width: 980px; padding-top: 2rem;}
    [data-testid="stChatMessage"] {border: 1px solid rgba(128,128,128,.16); border-radius: 14px; padding: 1rem;}
    .hero {padding: 1.25rem 1.4rem; border-radius: 18px; background: linear-gradient(120deg, rgba(83,115,255,.13), rgba(28,190,163,.10)); border: 1px solid rgba(128,128,128,.18);}
    .muted {color: #8b929d; font-size: .86rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='hero'><h1>🔎 RecallSearch</h1><p>Fast answers from the web, with a memory of what you asked and when.</p></div>", unsafe_allow_html=True)
st.caption("One agent tool: web search · Timestamped local memory · Source-linked answers")

if "session_id" not in st.session_state:
    requested_session = st.query_params.get("session")
    try:
        st.session_state.session_id = str(uuid.UUID(str(requested_session))) if requested_session else str(uuid.uuid4())
    except ValueError:
        st.session_state.session_id = str(uuid.uuid4())
    st.query_params["session"] = st.session_state.session_id

session_id = st.session_state.session_id
db_path = os.getenv("MEMORY_DB_PATH", "data/recallsearch.sqlite3")
memory = get_memory(db_path)

with st.sidebar:
    st.subheader("Your memory")
    st.caption(f"Times shown in {os.getenv('APP_TIMEZONE', 'Asia/Kolkata')}")
    if st.button("＋ New conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.query_params["session"] = st.session_state.session_id
        st.rerun()
    if st.button("Clear this conversation", use_container_width=True):
        memory.clear_session(session_id)
        st.rerun()

    st.divider()
    st.markdown("**Recent questions**")
    user_rows = [row for row in memory.list_messages(session_id, 100) if row["role"] == "user"]
    if not user_rows:
        st.caption("Your questions will appear here with timestamps.")
    for row in reversed(user_rows[-12:]):
        with st.container(border=True):
            st.caption(display_time(row["created_at_utc"]))
            st.write(row["content"][:150] + ("…" if len(row["content"]) > 150 else ""))
    st.divider()
    st.caption("Memory stays in the local SQLite database. It is not sent as a separate tool call; relevant past questions are added to the model context when useful.")

if not os.getenv("OPENAI_API_KEY"):
    st.warning("Add OPENAI_API_KEY to your .env file to start chatting. See .env.example.")

for row in memory.list_messages(session_id, 100):
    with st.chat_message(row["role"]):
        st.markdown(row["content"])
        if row["role"] == "assistant":
            try:
                sources = json.loads(row.get("sources_json", "[]"))
            except json.JSONDecodeError:
                sources = []
            if sources:
                with st.expander("Sources"):
                    for source in sources:
                        st.markdown(f"- [{source.get('title', source.get('url', 'Source'))}]({source.get('url', '#')})")
            if row.get("searched_web"):
                st.caption("Web search used")

prompt = st.chat_input("Ask a question. You can also ask what you asked earlier and when.")
if prompt:
    prior_history = memory.recent_context(session_id, limit=10)
    timestamped_memory = memory.memory_context(session_id, prompt)
    memory.add_message(session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Researching…" if any(word in prompt.lower() for word in ("latest", "current", "today", "recent", "price", "news")) else "Thinking…"):
                reply = WebSearchAgent().answer(prompt, history=prior_history, memory_context=timestamped_memory)
            st.markdown(reply.text)
            if reply.sources:
                with st.expander("Sources"):
                    for source in reply.sources:
                        st.markdown(f"- [{source.title}]({source.url})")
            if reply.searched_web:
                st.caption("Web search used · Sources attached")
            memory.add_message(
                session_id,
                "assistant",
                reply.text,
                sources_json=json.dumps([{"title": source.title, "url": source.url} for source in reply.sources]),
                searched_web=reply.searched_web,
            )
        except Exception as exc:  # user-facing, non-secret error handling
            message = str(exc)
            if "api_key" in message.lower() or "authentication" in message.lower():
                st.error("OpenAI authentication failed. Check that OPENAI_API_KEY is valid in your .env file.")
            else:
                st.error(f"I couldn't complete that request. {message[:300]}")
            st.caption("Your question was saved to this conversation's local memory.")
