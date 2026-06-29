from main import (
    calculate_knowledge_coverage,
    calculate_knowledge_index,
    derive_knowledge_rating,
    evaluate_case,
)


def test_calculate_knowledge_coverage():
    case = {
        "documents": [
            {"relevant": True},
            {"relevant": True},
            {"relevant": False},
        ]
    }

    result = calculate_knowledge_coverage(case)

    assert result == 66.7


def test_calculate_knowledge_coverage_returns_zero_without_documents():
    case = {"documents": []}

    result = calculate_knowledge_coverage(case)

    assert result == 0.0


def test_calculate_knowledge_index_uses_coverage_for_v1():
    case = {
        "documents": [
            {"relevant": True},
            {"relevant": False},
        ]
    }

    result = calculate_knowledge_index(case)

    assert result == 50.0


def test_derive_knowledge_rating():
    assert derive_knowledge_rating(0) == "Seed"
    assert derive_knowledge_rating(39.9) == "Seed"
    assert derive_knowledge_rating(40) == "Bronze"
    assert derive_knowledge_rating(55) == "Silver"
    assert derive_knowledge_rating(70) == "Gold"
    assert derive_knowledge_rating(85) == "Platinum"
    assert derive_knowledge_rating(95) == "Diamond"


def test_evaluate_case():
    case = {
        "id": "healthcare-antibiotic-delay-001",
        "query": "antibiotic delivery delay",
        "documents": [
            {"id": "doc-1", "text": "Relevant one", "relevant": True},
            {"id": "doc-2", "text": "Relevant two", "relevant": True},
            {"id": "doc-3", "text": "Irrelevant", "relevant": False},
        ],
    }

    result = evaluate_case(case)

    assert result["id"] == "healthcare-antibiotic-delay-001"
    assert result["query"] == "antibiotic delivery delay"
    assert result["documents"] == 3
    assert result["relevant_knowledge"] == 2
    assert result["irrelevant_knowledge"] == 1
    assert result["knowledge_coverage"] == 66.7
    assert result["knowledge_index"] == 66.7
    assert result["knowledge_rating"] == "Silver"