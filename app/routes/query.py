from fastapi import APIRouter, HTTPException
from app.services.data_service import get_table_data

router = APIRouter()

@router.get("/data/{table_name}")
def read_table_data(table_name: str, limit: int = 10, offset: int = 0):
    try:
        records = get_table_data(table_name, limit=limit, offset=offset)
        return {
            "table": table_name,
            "count": len(records),
            "data": records,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
