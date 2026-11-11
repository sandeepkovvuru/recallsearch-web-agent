from memory import SQLiteMemory


def test_messages_are_saved_with_utc_timestamps_and_order(tmp_path):
    memory = SQLiteMemory(tmp_path / "memory.sqlite3")
    memory.add_message("session-a", "user", "What is the latest Power BI release?")
    memory.add_message("session-a", "assistant", "I would verify the official release notes.")

    rows = memory.list_messages("session-a")
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["created_at_utc"].endswith("Z")
    assert rows[0]["content"] == "What is the latest Power BI release?"


def test_relevant_question_recall(tmp_path):
    memory = SQLiteMemory(tmp_path / "memory.sqlite3")
    memory.add_message("session-a", "user", "Find current Salesforce data analyst jobs in Hyderabad")
    memory.add_message("session-a", "assistant", "Here are the matching roles.")
    memory.add_message("session-a", "user", "Explain a Python list comprehension")

    matches = memory.relevant_questions("session-a", "Salesforce jobs in Hyderabad")
    assert matches
    assert "Salesforce" in matches[0]["content"]
    assert "created_at_utc" in matches[0]


def test_sessions_are_isolated_and_can_be_cleared(tmp_path):
    memory = SQLiteMemory(tmp_path / "memory.sqlite3")
    memory.add_message("session-a", "user", "Remember this")
    memory.add_message("session-b", "user", "Keep this separate")

    memory.clear_session("session-a")
    assert memory.list_messages("session-a") == []
    assert len(memory.list_messages("session-b")) == 1
