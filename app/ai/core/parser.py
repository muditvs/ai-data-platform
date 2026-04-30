import difflib
import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain import LLMChain, PromptTemplate

try:
    from langchain.llms import GoogleGemini
except ImportError:
    from langchain.google_genai import GoogleGemini

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
SUPPORTED_OPERATORS = {"eq", "gt", "lt", "gte", "lte", "like", "in", "between"}

PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["query", "schema_text", "allowed_tables_text", "table_hint_text"],
    template=(
        "You are a parser that converts a natural language data query into strict JSON filters for a table API. "
        "Use only the schema provided. Do not hallucinate table or column names. Do not generate SQL. "
        "Output only valid JSON and nothing else.\n\n"
        "Schema:\n{schema_text}\n\n"
        "Allowed tables: {allowed_tables_text}\n"
        "Table hint: {table_hint_text}\n\n"
        "User query: {query}\n\n"
        "Output JSON exactly in this shape:\n"
        "{\"table\": \"<table_name>\", \"filters\": {\"<column_operator>\": <value>}}\n"
        "Rules:\n"
        "- Only use these operators: eq, gt, lt, gte, lte, like, in, between.\n"
        "- Use only tables and columns from the schema.\n"
        "- If the user does not specify a filter, return \"filters\": {}.\n"
        "- If a table is already known, use that table.\n"
        "- If a column is not exact, choose the closest matching column name.\n"
    )
)


def _create_llm() -> Any:
    kwargs = {"temperature": 0}
    if GEMINI_API_KEY:
        kwargs["api_key"] = GEMINI_API_KEY
    try:
        return GoogleGemini(model=GEMINI_MODEL, **kwargs)
    except TypeError:
        return GoogleGemini(**kwargs)


def _schema_text(schema: dict[str, list[str]]) -> str:
    lines = []
    for table, columns in sorted(schema.items()):
        lines.append(f"{table}: {', '.join(columns)}")
    return "\n".join(lines)


def _safe_parse_json(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Parser output did not contain valid JSON")
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("Parser output could not be decoded as JSON") from exc


def _normalize_column_name(column: str, valid_columns: dict[str, str]) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", column).strip("_").lower()
    if normalized in valid_columns:
        return valid_columns[normalized]

    fuzzy = difflib.get_close_matches(normalized, list(valid_columns.keys()), n=1, cutoff=0.4)
    if fuzzy:
        return valid_columns[fuzzy[0]]

    substring_matches = [name for name in valid_columns if normalized in name or name in normalized]
    if substring_matches:
        return valid_columns[substring_matches[0]]

    raise ValueError(f"Unknown column: {column}")


def _normalize_filter_key(filter_key: str, allowed_columns: list[str]) -> str:
    valid_columns = {col.lower(): col for col in allowed_columns}
    if "_" in filter_key:
        candidate, _, operator = filter_key.rpartition("_")
        if operator not in SUPPORTED_OPERATORS:
            candidate = filter_key
            operator = "eq"
    else:
        candidate = filter_key
        operator = "eq"

    column_name = _normalize_column_name(candidate, valid_columns)
    if operator == "eq":
        return column_name
    return f"{column_name}_{operator}"


def parse_query(query: str, schema: dict[str, list[str]], table_hint: str | None = None) -> dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("Query text is required")

    schema_text = _schema_text(schema)
    allowed_tables = ", ".join(sorted(schema.keys()))
    table_hint_text = table_hint or "Choose the best matching table from the allowed tables"

    llm = _create_llm()
    chain = LLMChain(llm=llm, prompt=PROMPT_TEMPLATE)
    raw_output = chain.run(
        {
            "query": query,
            "schema_text": schema_text,
            "allowed_tables_text": allowed_tables,
            "table_hint_text": table_hint_text,
        }
    )

    parsed = _safe_parse_json(raw_output)
    if not isinstance(parsed, dict):
        raise ValueError("Parser returned invalid JSON structure")

    table = parsed.get("table")
    filters = parsed.get("filters")
    if not table or not isinstance(table, str):
        raise ValueError("Parser JSON must include a valid table name")
    if filters is None or not isinstance(filters, dict):
        raise ValueError("Parser JSON must include a filters object")

    if table_hint and table.lower() != table_hint.lower():
        raise ValueError("Parser returned a table that does not match the requested table")

    if table not in schema:
        raise ValueError(f"Parser selected an unknown table: {table}")

    normalized_filters: dict[str, Any] = {}
    for key, value in filters.items():
        normalized_key = _normalize_filter_key(str(key), schema[table])
        normalized_filters[normalized_key] = value

    return {"table": table, "filters": normalized_filters}
