import pandas as pd
import os
import re
from sqlalchemy import text
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
        df.columns = ( df.columns.str.lower().str.replace(r'\W+', '_', regex=True))  # Standardize column names

        # Generate table name dynamically
        base_name = os.path.basename(file_path)
        table_name = re.sub(r'\W+', '_', table_name)

        # Store the DataFrame into SQL database
        df.to_sql(table_name, engine, if_exists='replace', index=False)

        # Return dictionary
        return {
            "table_name": table_name,
            "rows": len(df),
            "columns": len(df.columns)
        }

    except Exception as e:
        raise Exception(f"Error processing file {file_path}: {e}")


def get_table_data(table_name: str, limit: int = 10, offset: int = 0):
    if not re.match(r'^[A-Za-z0-9_]+$', table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")

    query = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")

    try:
        df = pd.read_sql(query, engine, params={"limit": limit, "offset": offset})
        return df.to_dict(orient="records")
    except SQLAlchemyError as exc:
        message = str(exc).lower()
        if 'no such table' in message:
            raise ValueError(f"Table not found: {table_name}")
        raise
