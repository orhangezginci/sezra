from main import build_investigation_search_text


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