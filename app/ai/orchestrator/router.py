from typing import Optional


def route_query(query: str, table_name: Optional[str] = None) -> str:
    if table_name:
        return "sql"

    lower_query = query.lower()
    rag_keywords = [
        "document",
        "knowledge",
        "file",
        "upload",
        "context",
        "search",
        "rag",
        "qa",
    ]

    for keyword in rag_keywords:
        if keyword in lower_query:
            return "rag"

    return "sql"
