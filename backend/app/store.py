import json
import os
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

JSON_FIELDS = (
    "plan",
    "subagent_executions",
    "citation_verifications",
    "evaluation",
    "forecast",
    "disagreements",
    "projections",
    "brainstormed_ideas",
    "overcome_strategies",
    "active_speaker",
    "core_architecture",
    "attempt_history",
    "intake",
    "clarifying_questions",
    "scope",
    "pain_points",
    "transcript",
    "problem_candidates",
    "evidence",
    "gaps",
    "ideas",
    "critiques",
    "lineage",
    "validation_results",
    "ranked_ideas",
    "checkpoints",
    "spend",
    "limits",
)

SCALAR_FIELDS = (
    "panel_round",
    "convergence",
    "mode",
)


class EvidenceStore:
    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "foresightforge-local"),
            ),
        )

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    def initialize(self) -> None:
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT run_id IF NOT EXISTS FOR (n:Run) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (n:Claim) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE")

    def save_run(self, run: dict[str, Any]) -> None:
        with self.driver.session() as session:
            session.execute_write(self._save_run, run)

    @staticmethod
    def _save_run(tx: Any, run: dict[str, Any]) -> None:
        json_payload = {field: json.dumps(run.get(field)) for field in JSON_FIELDS}
        tx.run(
            """MERGE (r:Run {id: $id})
            SET r.domain = $domain, r.question = $question, r.status = $status,
                r.round = $round, r.current_stage = $current_stage,
                r.attempt = $attempt, r.max_attempts = $max_attempts,
                r.mode = $mode, r.panel_round = $panel_round,
                r.convergence = $convergence,
                r.plan = $plan, r.subagent_executions = $subagent_executions,
                r.citation_verifications = $citation_verifications,
                r.evaluation = $evaluation, r.forecast = $forecast,
                r.disagreements = $disagreements, r.projections = $projections,
                r.brainstormed_ideas = $brainstormed_ideas,
                r.overcome_strategies = $overcome_strategies,
                r.active_speaker = $active_speaker,
                r.core_architecture = $core_architecture,
                r.attempt_history = $attempt_history,
                r.intake = $intake, r.clarifying_questions = $clarifying_questions,
                r.scope = $scope, r.pain_points = $pain_points,
                r.transcript = $transcript, r.problem_candidates = $problem_candidates,
                r.evidence = $evidence, r.gaps = $gaps, r.ideas = $ideas,
                r.critiques = $critiques, r.lineage = $lineage,
                r.validation_results = $validation_results,
                r.ranked_ideas = $ranked_ideas, r.checkpoints = $checkpoints,
                r.spend = $spend, r.limits = $limits,
                r.created_at = $created_at, r.updated_at = $updated_at""",
            **{
                "id": run.get("id", ""),
                "domain": run.get("domain", ""),
                "question": run.get("question", ""),
                "status": run.get("status", "failed"),
                "round": run.get("round", 1),
                "current_stage": run.get("current_stage", "verify"),
                "created_at": run.get("created_at", ""),
                "updated_at": run.get("updated_at", ""),
                **json_payload,
                "attempt": run.get("attempt", 1),
                "max_attempts": run.get("max_attempts", 1),
                "mode": run.get("mode", "problem"),
                "panel_round": run.get("panel_round", 0),
                "convergence": float(run.get("convergence", 0.0) or 0.0),
            },
        )
        for source in run.get("sources", []):
            # Every parameter is supplied explicitly. Spreading the source dict
            # would make the query fail whenever a record is missing a field,
            # which is exactly what happens when a partially-populated run is
            # saved back after a checkpoint or a control action.
            tx.run(
                """MERGE (s:Source {id: $id})
                SET s.url = $url, s.title = $title, s.excerpt = $excerpt,
                    s.content = $content, s.search_snippet = $search_snippet,
                    s.published_at = $published_at, s.publisher = $publisher,
                    s.search_query = $search_query, s.provider = $provider,
                    s.retrieved_at = $retrieved_at
                WITH s MATCH (r:Run {id: $run_id}) MERGE (r)-[:HAS_SOURCE]->(s)""",
                run_id=run["id"],
                id=source.get("id", ""),
                url=source.get("url", ""),
                title=source.get("title", ""),
                excerpt=source.get("excerpt", ""),
                content=source.get("content", ""),
                search_snippet=source.get("search_snippet", ""),
                published_at=source.get("published_at"),
                publisher=source.get("publisher", ""),
                search_query=source.get("query", source.get("search_query", "")),
                provider=source.get("provider", ""),
                retrieved_at=source.get("retrieved_at", ""),
            )
        for claim in run.get("claims", []):
            tx.run(
                """MERGE (c:Claim {id: $id})
                SET c.text = $text, c.status = $status, c.confidence = $confidence,
                    c.author = $author
                WITH c MATCH (r:Run {id: $run_id}) MERGE (r)-[:HAS_CLAIM]->(c)""",
                run_id=run["id"],
                id=claim.get("id", ""),
                text=claim.get("text", ""),
                status=claim.get("status", "proposed"),
                confidence=claim.get("confidence", 0.0),
                author=claim.get("author", "unknown"),
            )
            for source_id in claim.get("source_ids", []):
                tx.run(
                    """MATCH (c:Claim {id: $claim_id}), (s:Source {id: $source_id})
                    MERGE (c)-[:SUPPORTED_BY]->(s)""",
                    claim_id=claim.get("id", ""), source_id=source_id,
                )
        for index, event in enumerate(run.get("audit", [])):
            tx.run(
                """MERGE (e:AuditEvent {id: $id})
                SET e.stage = $stage, e.event = $event, e.detail = $detail
                WITH e MATCH (r:Run {id: $run_id}) MERGE (r)-[:HAS_EVENT]->(e)""",
                id=f"{run.get('id', '')}:{index}", run_id=run.get("id", ""),
                stage=event.get("stage", ""),
                event=event.get("event", ""),
                detail=event.get("detail", ""),
            )

    @staticmethod
    def _source_record(node: Any) -> dict[str, Any]:
        source = dict(node)
        if "search_query" in source:
            source["query"] = source.pop("search_query")
        return source

    @staticmethod
    def _run_record(node: Any) -> dict[str, Any]:
        """Decode a Run node, restoring JSON-encoded R&D state fields."""
        run = dict(node)
        for field in JSON_FIELDS:
            raw = run.get(field)
            if isinstance(raw, str) and raw:
                try:
                    run[field] = json.loads(raw)
                except json.JSONDecodeError:
                    run.pop(field, None)
            elif raw in (None, ""):
                run.pop(field, None)
        for field in SCALAR_FIELDS:
            if field in run and run[field] in (None, ""):
                run.pop(field, None)
        run.setdefault("mode", "problem")
        run.setdefault("spend", {"usd": 0.0, "tokens": 0, "calls": 0})
        return run

    def list_runs(self) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            records = session.run(
                """MATCH (r:Run)
                OPTIONAL MATCH (r)-[:HAS_CLAIM]->(c:Claim)
                WITH r, collect(DISTINCT c) AS claims
                OPTIONAL MATCH (r)-[:HAS_SOURCE]->(s:Source)
                WITH r, claims, collect(DISTINCT s) AS sources
                OPTIONAL MATCH (r)-[:HAS_EVENT]->(e:AuditEvent)
                RETURN r, claims, sources, collect(DISTINCT e) AS audit
                ORDER BY r.updated_at DESC LIMIT 50"""
            )
            return [
                {
                    **self._run_record(record["r"]),
                    "claims": [dict(node) for node in record["claims"] if node],
                    "sources": [self._source_record(node) for node in record["sources"] if node],
                    "audit": [dict(node) for node in record["audit"] if node],
                }
                for record in records
            ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.driver.session() as session:
            record = session.run(
                """MATCH (r:Run {id: $id})
                OPTIONAL MATCH (r)-[:HAS_CLAIM]->(c:Claim)
                WITH r, collect(DISTINCT c) AS claims
                OPTIONAL MATCH (r)-[:HAS_SOURCE]->(s:Source)
                WITH r, claims, collect(DISTINCT s) AS sources
                OPTIONAL MATCH (r)-[:HAS_EVENT]->(e:AuditEvent)
                RETURN r, claims, sources, collect(DISTINCT e) AS audit""",
                id=run_id,
            ).single()
            if not record:
                return None
            return {
                **self._run_record(record["r"]),
                "claims": [dict(node) for node in record["claims"] if node],
                "sources": [self._source_record(node) for node in record["sources"] if node],
                "audit": [dict(node) for node in record["audit"] if node],
            }