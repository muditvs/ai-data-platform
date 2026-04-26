from fastapi import APIRouter, HTTPException, Request
from app.services.data_service import get_filtered_data

router = APIRouter()

@router.get("/data/{table_name}")
async def read_table_data(table_name: str, request: Request):
    query_params = dict(request.query_params)

    try:
        limit = int(query_params.pop("limit", 10))
        offset = int(query_params.pop("offset", 0))
    except ValueError:
        raise HTTPException(status_code=400, detail="limit and offset must be integer values")

    try:
        records = get_filtered_data(
            table_name,
            limit=limit,
            offset=offset,
            filters=query_params,
        )
        return {
            "table": table_name,
            "count": len(records),
            "data": records,
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
