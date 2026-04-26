import pandas as pd
import os
import re
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import engine


def process_data(file_path):
    try:
        # Detect file type
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext == '.xlsx':
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}. Only .csv and .xlsx are supported.")

        # Perform basic data cleaning
        df.dropna(how='all', inplace=True)  # Remove empty rows
        df.columns = df.columns.str.lower().str.replace(r'\W+', '_', regex=True)  # Standardize column names

        # Generate table name dynamically
        base_name = os.path.basename(file_path)
        name = os.path.splitext(base_name)[0]
        table_name = re.sub(r'\W+', '_', name.lower())

        # Store the DataFrame into SQL database
        df.to_sql(table_name, engine, if_exists='replace', index=False)

        return {
            "table_name": table_name,
            "rows": len(df),
            "columns": len(df.columns),
        }

    except Exception as e:
        raise Exception(f"Error processing file {file_path}: {e}")


def _get_table_columns(table_name: str):
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
    except Exception:
        raise LookupError(f"Table not found: {table_name}")

    if not columns:
        raise LookupError(f"Table not found: {table_name}")

    return [column["name"] for column in columns]


def get_filtered_data(
    table_name: str,
    limit: int = 10,
    offset: int = 0,
    filters: dict | None = None,
):
    if not re.match(r'^[A-Za-z0-9_]+$', table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")

    valid_columns = _get_table_columns(table_name)
    filters = filters or {}
    conditions = []
    params = {}

    operator_map = {
        "eq": "=",
        "gt": ">",
        "lt": "<",
        "gte": ">=",
        "lte": "<=",
        "like": "LIKE",
    }

    valid_columns_lower = {col.lower(): col for col in valid_columns}

    for key, value in filters.items():
        if not re.match(r'^[A-Za-z0-9_]+$', key):
            raise ValueError(f"Invalid filter field: {key}")

        if "_" in key:
            column, _, last_part = key.rpartition("_")
            if last_part in operator_map:
                op = last_part
            else:
                column = key
                op = "eq"   
        else:
            column = key
            op = "eq"

        column = column.lower()

        if column not in valid_columns_lower:
            raise ValueError(f"Invalid filter field: {column}")

        actual_column = valid_columns_lower[column]

        if op not in operator_map:
            raise ValueError(f"Invalid operator: {op}")

        sql_op = operator_map[op]
        param_name = f"{column}_{op}"
        conditions.append(f"{actual_column} {sql_op} :{param_name}")
        if op == "like":
            params[param_name] = f"%{value}%"
        else:
            params[param_name] = value

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = text(
        f"SELECT * FROM {table_name} {where_clause} LIMIT :limit OFFSET :offset"
    )

    params["limit"] = limit
    params["offset"] = offset

    try:
        df = pd.read_sql(query, engine, params=params)
        return df.to_dict(orient="records")
    except SQLAlchemyError as exc:
        message = str(exc).lower()
        if 'no such table' in message:
            raise LookupError(f"Table not found: {table_name}")
        raise
