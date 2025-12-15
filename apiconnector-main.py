# backend/app/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

from app.core.config import settings
from app.services.llm_service import LLMService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

# ---- CORS ----
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- DB helper (safe SELECT-only execution) ----
def execute_select(sql: str):
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    if ";" in sql:
        raise ValueError("Multiple SQL statements are not allowed")

    conn = sqlite3.connect(settings.SAP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    conn.close()
    return columns, rows


# ---- Models ----
class NLQuery(BaseModel):
    question: str


# ---- Routes ----

@app.get("/")
def root_controller():
    return {"status": "healthy"}


@app.post("/nl-query")
async def natural_language_query(payload: NLQuery):
    """
    Flow:
    1. User asks question
    2. LLM generates SQL
    3. SQLite executes SQL
    4. If intent is LIST/SHOW → return raw DB rows
       Else → return LLM explanation
    """
    llm = LLMService()

    try:
        # 1️⃣ NL → SQL
        sql = await llm.nl_to_sql(payload.question)

        # 2️⃣ SQL → DB
        columns, rows = execute_select(sql)

        # 3️⃣ Decide response style
        question_lower = payload.question.lower().strip()

        if question_lower.startswith(("list", "show", "display", "give")):
            # Return RAW database values (SAP-style)
            answer = "\n".join(
                ", ".join(str(v) for v in row)
                for row in rows
            )
        else:
            # Business explanation (LLM)
            answer = await llm.summarize_results(
                payload.question, columns, rows
            )

        return {
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "answer": answer,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Local run ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
