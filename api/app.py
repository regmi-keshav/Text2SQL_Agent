from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.models import SQLAgentRequest
from api.service import run_sql_agent

app = FastAPI(title="Text2SQLAgent API", version="1.0.0")


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/agent/sql")
def agent_sql(request: SQLAgentRequest):
    response = run_sql_agent(request.question)
    status_code = 200 if response.status == "success" else 500
    return JSONResponse(status_code=status_code, content=response.model_dump())
