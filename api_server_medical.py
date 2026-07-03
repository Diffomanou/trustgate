"""

EN : HTTP server for the UNSECURED medical agent.
     Exposed at http://localhost:8002/process
     to demonstrate that TrustGate detects real vulnerabilities
     on an agent from a completely different domain.

     LAUNCH ORDER FOR VIDEO DEMO:
       Terminal 1 : python api_server_medical.py   (port 8002)
       Terminal 2 : python dashboard.py            (port 8000)

     URL to paste in TrustGate: http://localhost:8002/process

     Role to describe: Medical assistant that answers patient health
     questions and provides access to medical records
"""

from __future__ import annotations
import sys
import logging

sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.trustgate.target.medical_agent import process_request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MedAssist — Medical Agent API (UNSECURED DEMO)",
    description=(
        "⚠️ INTENTIONALLY UNSECURED for TrustGate demonstration purposes. "
        "This agent has no security guardrails and will fail STRIDE security tests. "
        "Never deploy this in production."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MedicalRequest(BaseModel):
    content: str
    role: str = "user"


class MedicalResponse(BaseModel):
    status: str
    message: str
    human_review_required: bool
    data: dict | list | None = None


@app.get("/")
async def root():
    return {
        "name":        "MedAssist — Medical Agent",
        "security":    "⚠️ UNSECURED — for TrustGate demo only",
        "status":      "running",
        "endpoint":    "POST /process",
        "test_with":   "TrustGate at http://localhost:8000",
        "warning":     "This agent has NO security guardrails. It will fail STRIDE tests.",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/process", response_model=MedicalResponse)
async def process(request: MedicalRequest):
    logger.info(
        "[REQUEST] role=%s | content=%.80s",
        request.role, request.content
    )

    result = process_request({"content": request.content, "role": request.role})

    logger.info(
        "[RESPONSE] status=%s | human_review=%s",
        result.get("status"),
        result.get("human_review_required"),
    )

    return MedicalResponse(
        status=result.get("status", "ok"),
        message=result.get("message", ""),
        human_review_required=bool(result.get("human_review_required", False)),
        data=result.get("data"),
    )


if __name__ == "__main__":
    print("\n" + "=" * 58)
    print("  MedAssist — Medical Agent (UNSECURED DEMO)")
    print("  Running at : http://localhost:8002")
    print("  Docs       : http://localhost:8002/docs")
    print("")
    print("  ⚠️  This agent has NO security guardrails.")
    print("  TrustGate WILL find vulnerabilities here.")
    print("")
    print("  Paste this URL in TrustGate dashboard:")
    print("  http://localhost:8002/process")
    print("")
    print("  Role to describe in TrustGate:")
    print("  Medical assistant that answers patient health")
    print("  questions and provides access to medical records")
    print("")
    print("  Ctrl+C to stop")
    print("=" * 58 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
