import json


def _describe_filters(filters: dict) -> str:
    if not filters:
        return "no filters"

    descriptions = []
    for key, value in filters.items():
        if "_" in key:
            column, _, operator = key.rpartition("_")
        else:
            column = key
            operator = "eq"
        descriptions.append(f"{column.replace('_', ' ')} {operator} {value}")

    return ", ".join(descriptions)


def build_response(query: str, table: str, filters: dict, api_payload: dict) -> str:
    rows = api_payload.get("data", [])
    count = len(rows)
    if count == 0:
        return f"No records found in {table} matching your query."

    filter_text = _describe_filters(filters)
    sample_rows = rows[:3]
    sample_json = json.dumps(sample_rows, default=str, ensure_ascii=False)

    return (
        f"Found {count} record{'s' if count != 1 else ''} in {table} with {filter_text}. "
        f"Sample results: {sample_json}"
    )
