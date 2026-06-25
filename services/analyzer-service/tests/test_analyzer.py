from main import build_investigation_search_text, build_investigation_summary
from main import search_semantic_evidence, create_investigation_event
from main import derive_investigation_subject, derive_evidence_type


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
    event = {"payload": {}}

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

class FakeInvestigationRequestPoint:
    score = 0.9
    payload = {
    "event_id": "investigation-123",
    "event_type": "InvestigationRequested",
    "source": "demo-script",
    "text": '{"reason":"human_reported_issue"}',
    "payload": {
        "reason": "human_reported_issue",
        "subject": "antibiotic dose delayed",
    },
}


class FakeInvestigationRequestResponse:
    points = [FakeInvestigationRequestPoint()]


class FakeInvestigationRequestQdrantClient:
    def query_points(self, collection_name, query, limit):
        return FakeInvestigationRequestResponse()
    
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
    "evidence_type": "unknown",
    }  
    ]

def test_search_semantic_evidence_excludes_current_investigation_request():
    result = search_semantic_evidence(
        qdrant_client=FakeInvestigationRequestQdrantClient(),
        embedding_model=FakeEmbeddingModel(),
        search_text="test",
        excluded_event_id="investigation-123",
    )

    assert result == []

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
        "payload": {
            "subject": "antibiotic dose delayed",
        },
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

    assert result["payload"]["subject"] == "antibiotic dose delayed"
    assert result["payload"]["summary"] == "Test summary"
    assert result["payload"]["evidence"] == evidence

def test_derive_evidence_type_detects_measurement_from_metric():
    evidence = {
        "payload": {
            "metric": "antibiotic_restock_delay_minutes",
        }
    }

    result = derive_evidence_type(evidence)

    assert result == "measurement"


def test_derive_evidence_type_detects_measurement_from_value():
    evidence = {
        "payload": {
            "value": 47,
        }
    }

    result = derive_evidence_type(evidence)

    assert result == "measurement"


def test_derive_evidence_type_detects_message_from_email_fields():
    evidence = {
        "payload": {
            "from": "pharmacy@example.com",
            "subject": "Supplier change",
        }
    }

    result = derive_evidence_type(evidence)

    assert result == "message"


def test_derive_evidence_type_falls_back_to_unknown():
    evidence = {
        "payload": {
            "foo": "bar",
        }
    }

    result = derive_evidence_type(evidence)

    assert result == "unknown"
def test_derive_investigation_subject_uses_subject():
    event = {
        "payload": {
            "subject": "antibiotic dose delayed",
        }
    }

    result = derive_investigation_subject(event)

    assert result == "antibiotic dose delayed"


def test_derive_investigation_subject_falls_back_to_summary():
    event = {
        "payload": {
            "summary": "Patient reports delayed medication. Extra details follow.",
        }
    }

    result = derive_investigation_subject(event)

    assert result == "Patient reports delayed medication"


def test_derive_investigation_subject_falls_back_to_untitled():
    event = {
        "payload": {}
    }

    result = derive_investigation_subject(event)

    assert result == "Untitled investigation"
