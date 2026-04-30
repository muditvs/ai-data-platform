from app.services.data_service import get_data


def fetch_data(table: str, filters: dict, base_url: str | None = None) -> dict:
    if not table or not isinstance(table, str):
        raise ValueError("Table name is required for API query")

    records = get_data(table, filters or {})
    return {"data": records}
