"""

EN : HTTP server for the Ambient Expense Agent.
     It exposes the target agent at http://localhost:8001/process
     so TrustGate can test it via a real HTTP URL —
     exactly as if it were a production-deployed agent.

     Launch: python api_server.py
     URL to paste in TrustGate: http://localhost:8001/process
"""

from __future__ import annotations
import sys
import logging

sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.trustgate.target.expense_agent import process_expense

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S")

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ambient Expense Agent API",
    description=(
        "The Day-4 codelab expense-approval agent, exposed as an HTTP endpoint. "
        "Used as a real deployment target for TrustGate red-teaming."
    ),
    version="1.0.0",
)


# EN : Open CORS for local testing — never do this in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExpenseRequest(BaseModel):
    """
    
    EN : Expected input format. Matches exactly what TrustGate sends:
         {"content": "...", "role": "user"}.
    """
    content: str
    role: str = "user"


class ExpenseResponse(BaseModel):
    """
   
    EN : Output format — the keys TrustGate reads to evaluate whether
         the agent resisted the attack.
    """
    status: str
    message: str
    human_review_required: bool
    amount_usd: float | None = None


@app.get("/")
async def root():
    """
    EN : Home page — confirms the server is running.
    """
    return {
        "name":        "Ambient Expense Agent",
        "description": "Day-4 codelab agent — Kaggle 5-Day AI Agents Intensive 2026",
        "status":      "running",
        "endpoint":    "POST /process",
        "test_with":   "TrustGate at http://localhost:8000",
    }


@app.get("/health")
async def health():
    """
   
    EN : Health endpoint — used by TrustGate to verify the agent
         is reachable before launching the pipeline.
    """
    return {"status": "ok"}


@app.post("/process", response_model=ExpenseResponse)
async def process(request: ExpenseRequest):
    """
   
    EN : Main agent entry point.
         Receives a user message and returns the agent's decision.
         This is the endpoint TrustGate attacks with its 10 STRIDE test cases.
    """
    logger.info("[REQUEST] role=%s | content=%.80s", request.role, request.content)

    result = process_expense({"content": request.content, "role": request.role})

    logger.info(
        "[RESPONSE] status=%s | human_review=%s",
        result.get("status"),
        result.get("human_review_required"),
    )

    return ExpenseResponse(
        status=result.get("status", "unknown"),
        message=result.get("message", ""),
        human_review_required=bool(result.get("human_review_required", False)),
        amount_usd=result.get("amount_usd"),
    )


if __name__ == "__main__":
    print("\n" + "=" * 58)
    print("  Ambient Expense Agent — HTTP Server")
    print("  Running at : http://localhost:8001")
    print("  Docs       : http://localhost:8001/docs")
    print("")
    print("  Paste this URL in TrustGate dashboard:")
    print("  http://localhost:8001/process")
    print("")
    print("  Ctrl+C to stop")
    print("=" * 58 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
