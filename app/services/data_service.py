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


def parse_value(value):
    try:
        if isinstance(value, str) and "." in value:
            return float(value)
        return int(value)
    except Exception:
        return value


def get_filtered_data(
    table_name: str,
    limit: int = 10,
    offset: int = 0,
    filters: dict | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    fields: str | None = None,
    agg: str | None = None,
    group_by: str | None = None,
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
        "in": "IN",
        "between": "BETWEEN",
    }

    valid_columns_lower = {col.lower(): col for col in valid_columns}

    agg_mapping = {
        "avg": "AVG",
        "sum": "SUM",
        "min": "MIN",
        "max": "MAX",
    }

    if agg:
        agg_lower = agg.lower()
        if agg_lower == "count":
            agg_clause = " COUNT(*)"
            agg_column = None
        elif "_" in agg_lower:
            function, _, agg_column = agg_lower.partition("_")
            if function not in agg_mapping or not agg_column:
                raise ValueError(f"Invalid agg parameter: {agg}")
            if agg_column not in valid_columns_lower:
                raise ValueError(f"Invalid aggregation column: {agg_column}")
            agg_clause = f"{agg_mapping[function]}({valid_columns_lower[agg_column]})"
        else:
            raise ValueError(f"Invalid agg parameter: {agg}")

        if group_by:
            group_by_lower = group_by.lower()
            if group_by_lower not in valid_columns_lower:
                raise ValueError(f"Invalid group_by column: {group_by}")
            group_by_column = valid_columns_lower[group_by_lower]
            select_clause = f"SELECT {group_by_column}, {agg_clause}"
            group_by_clause = f"GROUP BY {group_by_column}"
        else:
            select_clause = f"SELECT {agg_clause}"
            group_by_clause = ""
    else:
        if group_by:
            raise ValueError("group_by requires agg parameter")

        if fields:
            selected_fields = [item.strip() for item in fields.split(",") if item.strip()]
            if not selected_fields:
                raise ValueError("fields must contain at least one column")
            select_columns = []
            for field in selected_fields:
                field_lower = field.lower()
                if field_lower not in valid_columns_lower:  
                    raise ValueError(f"Invalid field selection: {field}")
                select_columns.append(valid_columns_lower[field_lower])
            select_clause = f"SELECT {', '.join(select_columns)}"
        else:
            select_clause = "SELECT *"

        group_by_clause = ""

    order_clause = ""
    if sort_by:
        sort_by_lower = sort_by.lower()
        if sort_by_lower not in valid_columns_lower:
            raise ValueError(f"Invalid sort_by column: {sort_by}")
        normalized_order = order.lower()
        if normalized_order not in {"asc", "desc"}:
            raise ValueError("order must be 'asc' or 'desc'")
        order_clause = f"ORDER BY {valid_columns_lower[sort_by_lower]} {normalized_order.upper()}"

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

        if op == "in":
            if not isinstance(value, str):
                raise ValueError(f"Invalid IN filter value for {key}")

            values = [item.strip() for item in value.split(",") if item.strip()]
            if not values:
                raise ValueError(f"IN filter must contain at least one value: {key}")

            placeholders = []
            for index, item in enumerate(values):
                item_param = f"{param_name}_{index}"
                placeholders.append(f":{item_param}")
                params[item_param] = parse_value(item)

            conditions.append(f"{actual_column} {sql_op} ({', '.join(placeholders)})")
        elif op == "between":
            if not isinstance(value, str):
                raise ValueError(f"Invalid BETWEEN filter value for {key}")

            bounds = [item.strip() for item in value.split(",")]
            if len(bounds) != 2 or not bounds[0] or not bounds[1]:
                raise ValueError(f"BETWEEN filter must contain low and high values: {key}")

            low_param = f"{param_name}_low"
            high_param = f"{param_name}_high"
            params[low_param] = parse_value(bounds[0])
            params[high_param] = parse_value(bounds[1])
            conditions.append(
                f"{actual_column} {sql_op} :{low_param} AND :{high_param}"
            )
        else:
            conditions.append(f"{actual_column} {sql_op} :{param_name}")
            if op == "like":
                params[param_name] = f"%{value}%"
            else:
                params[param_name] = parse_value(value)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order_clause = order_clause or ""

    query = text(
        f"{select_clause} FROM {table_name} {where_clause} {group_by_clause} {order_clause} LIMIT :limit OFFSET :offset"
    )

    params["limit"] = limit
    params["offset"] = offset

    print("QUERY:", query)
    print("PARAMS:", params)

    try:
        df = pd.read_sql(query, engine, params=params)
        return df.to_dict(orient="records")
    except SQLAlchemyError as exc:
        message = str(exc).lower()
        if 'no such table' in message:
            raise LookupError(f"Table not found: {table_name}")
        raise
