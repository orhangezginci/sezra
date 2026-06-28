from main import build_semantic_text, create_enriched_event, update_lifecycle


def test_build_semantic_text_expands_scalar_fields():
    event = {
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "payload": {
            "metric": "antibiotic_delivery_delay_minutes",
            "value": 52,
            "labels": {
                "medication": "amoxicillin_iv",
                "department": "pharmacy",
            },
        },
    }

    result = build_semantic_text(event)

    assert "Event type: JsonFileReceived." in result
    assert "Source: manual test." in result
    assert "metric: antibiotic delivery delay minutes." in result
    assert "value: 52." in result
    assert "labels medication: amoxicillin iv." in result
    assert "labels department: pharmacy." in result


def test_create_enriched_event_preserves_original_payload_fields():
    event = {
        "event_id": "raw-1",
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "occurred_at": "2026-06-26T18:10:00Z",
        "correlation_id": None,
        "causation_id": None,
        "payload": {
            "metric": "antibiotic_delivery_delay_minutes",
            "value": 52,
        },
    }

    result = create_enriched_event(event)

    assert result["payload"]["metric"] == "antibiotic_delivery_delay_minutes"
    assert result["payload"]["value"] == 52


def test_create_enriched_event_adds_semantic_text():
    event = {
        "event_id": "raw-1",
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "occurred_at": "2026-06-26T18:10:00Z",
        "payload": {
            "metric": "antibiotic_delivery_delay_minutes",
            "value": 52,
        },
    }

    result = create_enriched_event(event)

    assert "semantic_text" in result["payload"]
    assert "antibiotic delivery delay minutes" in result["payload"]["semantic_text"]


def test_create_enriched_event_adds_enrichment_entry():
    event = {
        "event_id": "raw-1",
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "occurred_at": "2026-06-26T18:10:00Z",
        "payload": {},
    }

    result = create_enriched_event(event)

    enrichments = result["payload"]["enrichments"]

    assert isinstance(enrichments, list)
    assert enrichments[0]["level"] == 1
    assert enrichments[0]["service"] == "level-1-enricher-service"
    assert enrichments[0]["strategy"] == "generic scalar field expansion"


def test_create_enriched_event_adds_lifecycle_stage():
    event = {
        "event_id": "raw-1",
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "occurred_at": "2026-06-26T18:10:00Z",
        "payload": {},
    }

    result = create_enriched_event(event)

    assert result["lifecycle"]["stage"] == "enriched"
    assert result["lifecycle"]["history"][0]["stage"] == "enriched"
    assert result["lifecycle"]["history"][0]["service"] == "level-1-enricher-service"


def test_create_enriched_event_sets_causation_and_correlation():
    event = {
        "event_id": "raw-1",
        "event_type": "JsonFileReceived",
        "source": "manual-test",
        "occurred_at": "2026-06-26T18:10:00Z",
        "correlation_id": None,
        "causation_id": None,
        "payload": {},
    }

    result = create_enriched_event(event)

    assert result["causation_id"] == "raw-1"
    assert result["correlation_id"] == "raw-1"


def test_update_lifecycle_preserves_existing_history():
    event = {
        "lifecycle": {
            "stage": "received",
            "history": [
                {
                    "stage": "received",
                    "service": "json-file-adapter",
                    "occurred_at": "2026-06-26T18:00:00Z",
                }
            ],
        }
    }

    result = update_lifecycle(event, "enriched")

    assert result["stage"] == "enriched"
    assert len(result["history"]) == 2
    assert result["history"][0]["stage"] == "received"
    assert result["history"][1]["stage"] == "enriched"