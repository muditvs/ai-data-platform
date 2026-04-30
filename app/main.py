from fastapi import FastAPI
from app.routes import ai_query, upload, query

app = FastAPI()

app.include_router(upload)
app.include_router(query)
app.include_router(ai_query)

@app.get("/")
def home():
    return {"message": "AI Data Platform Running"}