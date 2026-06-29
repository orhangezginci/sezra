def calculate_knowledge_coverage(case: dict) -> float:
    documents = case.get("documents", [])

    if not documents:
        return 0.0

    relevant_count = sum(1 for document in documents if document.get("relevant") is True)

    return round((relevant_count / len(documents)) * 100, 1)


def calculate_knowledge_index(case: dict) -> float:
    return calculate_knowledge_coverage(case)


def derive_knowledge_rating(index: float) -> str:
    if index < 40:
        return "Seed"
    if index < 55:
        return "Bronze"
    if index < 70:
        return "Silver"
    if index < 85:
        return "Gold"
    if index < 95:
        return "Platinum"

    return "Diamond"


def evaluate_case(case: dict) -> dict:
    knowledge_index = calculate_knowledge_index(case)

    documents = case.get("documents", [])
    relevant_count = sum(1 for document in documents if document.get("relevant") is True)
    irrelevant_count = len(documents) - relevant_count

    return {
        "id": case.get("id"),
        "query": case.get("query"),
        "documents": len(documents),
        "relevant_knowledge": relevant_count,
        "irrelevant_knowledge": irrelevant_count,
        "knowledge_coverage": knowledge_index,
        "knowledge_index": knowledge_index,
        "knowledge_rating": derive_knowledge_rating(knowledge_index),
    }