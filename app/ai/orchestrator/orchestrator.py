# handles query delegation of work

from typing import Optional

from app.ai.pipelines.rag_pipeline import run_rag_pipeline
from app.ai.orchestrator.router import route_query
from app.ai.pipelines.sql_pipeline import run_sql_pipeline


def handle_query(user_query: str, table_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
    if not user_query or not user_query.strip():
        raise ValueError("The query field must not be empty")

    if table_name:
        table_name = table_name.strip()
        if not table_name:
            table_name = None

    route = route_query(user_query, table_name)
    if route == "sql":
        return run_sql_pipeline(user_query, table_name, base_url=base_url)
    if route == "rag":
        return run_rag_pipeline(user_query)

    raise ValueError(f"Unsupported query route: {route}")
