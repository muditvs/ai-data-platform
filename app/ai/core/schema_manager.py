import json
from pathlib import Path
from sqlalchemy import inspect
from app.db.database import engine

SCHEMA_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "schema_store.json"


def _ensure_store_file():
    SCHEMA_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_schema_store() -> dict:
    _ensure_store_file()
    if not SCHEMA_STORE_PATH.exists():
        return {}

    try:
        with SCHEMA_STORE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return {}


def _write_schema_store(schema: dict) -> None:
    _ensure_store_file()
    with SCHEMA_STORE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(schema, handle, indent=2)


def _extract_schema_from_db(table_name: str) -> list[str]:
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
    except Exception as exc:
        raise LookupError(f"Table not found: {table_name}") from exc

    if not columns:
        raise LookupError(f"Table not found: {table_name}")

    return [column["name"] for column in columns]


def get_table_schema(table_name: str) -> list[str]:
    schema = _load_schema_store()
    if table_name in schema:
        return schema[table_name]

    columns = _extract_schema_from_db(table_name)
    schema[table_name] = columns
    _write_schema_store(schema)
    return columns


def get_all_schemas() -> dict[str, list[str]]:
    schema = _load_schema_store()
    if schema:
        return schema

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    schema = {}
    for table in tables:
        try:
            columns = inspector.get_columns(table)
            schema[table] = [column["name"] for column in columns]
        except Exception:
            continue

    _write_schema_store(schema)
    return schema
