from fastapi import FastAPI
from app.routes import upload, query

app = FastAPI()

app.include_router(upload)
app.include_router(query)

@app.get("/")
def home():
    return {"message": "AI Data Platform Running"}