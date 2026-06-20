from main import build_investigation_search_text, build_investigation_summary
from main import search_semantic_evidence, create_investigation_event



def test_build_investigation_search_text():
    event = {
        "payload": {
            "reason": "human_reported_issue",
            "subject": "antibiotic dose delayed",
            "summary": "Patient family reports delay.",
        }
    }

    result = build_investigation_search_text(event)

    assert "human_reported_issue" in result
    assert "antibiotic dose delayed" in result
    assert "Patient family reports delay." in result

def test_build_investigation_search_text_with_empty_payload():
    event = {
        "payload": {}
    }

    result = build_investigation_search_text(event)

    assert result == ""

class FakeEmbeddingModel:
    def encode(self, text):
        assert text == "test"
        return FakeVector()


class FakeVector:
    def tolist(self):
        return [0.1, 0.2, 0.3]


class FakePoint:
    score = 0.9
    payload = {
        "event_id": "event-1",
        "source": "test-source",
        "text": "test evidence",
        "payload": {"foo": "bar"},
    }


class FakeResponse:
    points = [FakePoint()]


class FakeQdrantClient:
    def query_points(self, collection_name, query, limit):
        assert collection_name == "sezra_events"
        assert query == [0.1, 0.2, 0.3]
        assert limit == 5
        return FakeResponse()


def test_search_semantic_evidence_returns_qdrant_results():
    result = search_semantic_evidence(
        qdrant_client=FakeQdrantClient(),
        embedding_model=FakeEmbeddingModel(),
        search_text="test",
    )

    assert result == [
        {
            "score": 0.9,
            "event_id": "event-1",
            "source": "test-source",
            "text": "test evidence",
            "payload": {"foo": "bar"},
        }
    ]
def test_build_investigation_summary():
    event = {
        "payload": {
            "subject": "antibiotic dose delayed",
        }
    }

    evidence = [
        {
            "text": "Patient complaint",
        },
        {
            "text": "Restock delay metric",
        },
    ]

    result = build_investigation_summary(
        event,
        evidence,
    )

    assert "antibiotic dose delayed" in result
    assert "Patient complaint" in result
    assert "Restock delay metric" in result


def test_create_investigation_event():
    investigation_event = {
        "event_id": "investigation-123",
    }

    evidence = [
        {
            "text": "Patient complaint",
        }
    ]

    result = create_investigation_event(
        investigation_event=investigation_event,
        evidence=evidence,
        summary="Test summary",
    )

    assert result["event_type"] == "InvestigationGenerated"
    assert result["source"] == "analyzer-service"
    assert result["correlation_id"] == "investigation-123"
    assert result["causation_id"] == "investigation-123"

    assert (
        result["payload"]["source_investigation_event_id"]
        == "investigation-123"
    )

    assert result["payload"]["summary"] == "Test summary"
    assert result["payload"]["evidence"] == evidence