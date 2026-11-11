from types import SimpleNamespace

from agent import WebSearchAgent, extract_sources


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.responses_api = FakeResponses(response)

    @property
    def responses(self):
        return self.responses_api


def make_response():
    annotation = SimpleNamespace(
        type="url_citation",
        url_citation=SimpleNamespace(title="Official source", url="https://example.com/fact"),
    )
    return SimpleNamespace(
        output_text="Verified answer. [Official source](https://example.com/fact)",
        output=[
            SimpleNamespace(type="web_search_call"),
            SimpleNamespace(type="message", content=[SimpleNamespace(annotations=[annotation])]),
        ],
        _request_id="req_test_123",
    )


def test_agent_exposes_only_web_search_tool():
    response = make_response()
    client = FakeClient(response)
    agent = WebSearchAgent(client=client, model="test-model")

    reply = agent.answer(
        "What changed recently?",
        history=[{"role": "user", "content": "Earlier question"}],
        memory_context="- [2026-11-10T09:00:00Z] Asked about the same topic",
    )

    kwargs = client.responses_api.kwargs
    assert kwargs["tools"] == [{"type": "web_search", "search_context_size": "low"}]
    assert kwargs["tool_choice"] == "auto"
    assert reply.searched_web is True
    assert reply.sources[0].url == "https://example.com/fact"
    assert reply.request_id == "req_test_123"
    assert len(kwargs["input"]) == 3
    assert "saved memory context" in kwargs["input"][0]["content"].lower()
    assert "asked about the same topic" not in kwargs["instructions"].lower()


def test_extract_sources_deduplicates_urls():
    annotation = {"type": "url_citation", "url_citation": {"title": "Example", "url": "https://example.com"}}
    response = {"output": [{"type": "message", "content": [{"annotations": [annotation, annotation]}]}]}
    assert len(extract_sources(response)) == 1


def test_blank_question_is_rejected():
    agent = WebSearchAgent(client=FakeClient(make_response()), model="test-model")
    try:
        agent.answer("   ")
    except ValueError as exc:
        assert "enter a question" in str(exc).lower()
    else:
        raise AssertionError("Expected blank prompt to be rejected")
