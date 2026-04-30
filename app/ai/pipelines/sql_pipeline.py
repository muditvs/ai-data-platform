from typing import Optional

from app.ai.core.data_gateway import fetch_data
from app.ai.core.parser import parse_query
from app.ai.core.response_generator import build_response
from app.ai.core.schema_manager import get_all_schemas, get_table_schema


def run_sql_pipeline(user_query: str, table_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
    if table_name:
        schema = {table_name: get_table_schema(table_name)}
    else:
        schema = get_all_schemas()
        if not schema:
            raise ValueError("No available schema found for query parsing")

    parsed = parse_query(user_query, schema, table_hint=table_name)
    api_payload = fetch_data(parsed["table"], parsed["filters"], base_url=base_url)
    return build_response(user_query, parsed["table"], parsed["filters"], api_payload)
