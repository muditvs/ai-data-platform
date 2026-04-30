from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.orchestrator.orchestrator import handle_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    table: str | None = None


class QueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=QueryResponse)
async def query_data(request: QueryRequest):
    try:
        answer = handle_query(request.query, request.table)
        return {"answer": answer}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
