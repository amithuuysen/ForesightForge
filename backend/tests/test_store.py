import json
from typing import Any

from app.store import EvidenceStore


class FakeResult:
    def __init__(self, record: dict[str, Any] | None = None) -> None:
        self.record = record

    def single(self) -> dict[str, Any] | None:
        return self.record

    def __iter__(self):
        return iter([])


class FakeSession:
    def __init__(self, record: dict[str, Any] | None = None) -> None:
        self.record = record
        self.queries: list[str] = []

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def run(self, query: str, **kwargs: Any) -> FakeResult:
        self.queries.append(query)
        return FakeResult(self.record)


class FakeDriver:
    def __init__(self, session: FakeSession) -> None:
        self.test_session = session

    def session(self) -> FakeSession:
        return self.test_session


def test_run_retrieval_queries_sources_directly_from_run() -> None:
    session = FakeSession()
    store = EvidenceStore.__new__(EvidenceStore)
    store.driver = FakeDriver(session)

    store.list_runs()

    assert "OPTIONAL MATCH (r)-[:HAS_SOURCE]->(s:Source)" in session.queries[0]


def test_run_lookup_keeps_unclaimed_source_metadata() -> None:
    source = {
        "id": "source-1",
        "url": "https://example.org/report",
        "title": "Research report",
        "excerpt": "Extracted text",
        "content": "Full extracted article text.",
        "search_snippet": "Search provider snippet",
        "published_at": "2025-02-10",
        "publisher": "Research Journal",
        "query": "battery storage research report",
        "provider": "ddgs",
        "retrieved_at": "2026-10-18T00:00:00+00:00",
    }
    session = FakeSession({"r": {"id": "run-1"}, "claims": [], "sources": [source], "audit": []})
    store = EvidenceStore.__new__(EvidenceStore)
    store.driver = FakeDriver(session)

    run = store.get_run("run-1")

    assert run is not None
    assert run["sources"] == [source]
    assert run["claims"] == []
    assert "OPTIONAL MATCH (r)-[:HAS_SOURCE]->(s:Source)" in session.queries[0]


def test_store_maps_search_query_to_api_query_field() -> None:
    mapped = EvidenceStore._source_record({"id": "source-1", "search_query": "a useful search"})

    assert mapped["query"] == "a useful search"
    assert "search_query" not in mapped


def test_run_lookup_decodes_json_encoded_rnd_state() -> None:
    """R&D council state is stored as JSON and must be restored on read."""
    architecture = {"system_name": "Transmon Qubit", "primitives": [{"name": "Josephson Junction"}]}
    session = FakeSession({
        "r": {
            "id": "run-1",
            "domain": "Quantum Qubits",
            "core_architecture": json.dumps(architecture),
            "forecast": json.dumps({"verdict": "PASS"}),
            "evaluation": json.dumps({"overall_score": 0.92}),
            "plan": "",
        },
        "claims": [],
        "sources": [],
        "audit": [],
    })
    store = EvidenceStore.__new__(EvidenceStore)
    store.driver = FakeDriver(session)

    run = store.get_run("run-1")

    assert run is not None
    assert run["core_architecture"]["system_name"] == "Transmon Qubit"
    assert run["forecast"]["verdict"] == "PASS"
    assert run["evaluation"]["overall_score"] == 0.92
    assert "plan" not in run


def test_save_run_encodes_rnd_state_as_json() -> None:
    class RecordingSession(FakeSession):
        def __init__(self) -> None:
            super().__init__()
            self.params: list[dict[str, Any]] = []

        def execute_write(self, fn: Any, *args: Any) -> None:
            session = self

            class RecordingTx:
                def run(self, _query: str, **kwargs: Any) -> None:
                    session.params.append(kwargs)

            fn(RecordingTx(), *args)

    session = RecordingSession()
    store = EvidenceStore.__new__(EvidenceStore)
    store.driver = FakeDriver(session)

    store.save_run({
        "id": "run-1",
        "domain": "Quantum Qubits",
        "question": "How to overcome TLS loss?",
        "status": "needs_evidence",
        "round": 1,
        "attempt": 2,
        "max_attempts": 2,
        "current_stage": "verify",
        "created_at": "2026-10-20T00:00:00+00:00",
        "updated_at": "2026-10-20T00:01:00+00:00",
        "claims": [],
        "sources": [],
        "audit": [],
        "core_architecture": {"system_name": "Transmon Qubit"},
    })

    assert session.params, "expected the run to be written"
    written = session.params[0]
    assert json.loads(written["core_architecture"])["system_name"] == "Transmon Qubit"


class RecordingTx:
    """Captures every parameter map passed to a Cypher statement."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, query: str, **kwargs: Any) -> FakeResult:
        self.calls.append((query, kwargs))
        return FakeResult(None)


def test_save_run_supplies_every_source_parameter() -> None:
    """A source missing optional fields must not break the save.

    The store used to spread the source dict straight into the query, so a
    record without `published_at` raised Neo.ClientError.Statement.
    ParameterMissing and the whole save failed.
    """
    tx = RecordingTx()
    EvidenceStore._save_run(
        tx,  # type: ignore[arg-type]
        {
            "id": "run-1",
            "domain": "batteries",
            "question": "q",
            "status": "completed",
            "round": 1,
            "current_stage": "verify",
            "created_at": "2026-10-20T00:00:00Z",
            "updated_at": "2026-10-20T00:00:00Z",
            "sources": [{"id": "src-1", "url": "https://example.org", "title": "T"}],
            "claims": [{"id": "c1", "text": "t"}],
            "audit": [{"stage": "s", "event": "e"}],
        },
    )

    source_call = next(
        (params for query, params in tx.calls if "MERGE (s:Source" in query), None
    )
    assert source_call is not None, "the source statement must have run"
    for key in (
        "id", "url", "title", "excerpt", "content", "search_snippet",
        "published_at", "publisher", "search_query", "provider", "retrieved_at",
    ):
        assert key in source_call, f"missing parameter: {key}"

    claim_call = next(
        (params for query, params in tx.calls if "MERGE (c:Claim" in query), None
    )
    assert claim_call is not None
    for key in ("id", "text", "status", "confidence", "author"):
        assert key in claim_call, f"missing parameter: {key}"

    audit_call = next(
        (params for query, params in tx.calls if "MERGE (e:AuditEvent" in query), None
    )
    assert audit_call is not None
    for key in ("id", "stage", "event", "detail"):
        assert key in audit_call, f"missing parameter: {key}"
