import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import Base, SessionLocal, engine
from graph import app_graph
from models import ClaimRecord, ReviewQueueRecord

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.middleware("http")
async def rewrite_double_slashes(request: Request, call_next):
    path = request.scope.get("path", "")
    if "//" in path:
        request.scope["path"] = path.replace("//", "/")
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Claim(BaseModel):
    text: str

@app.get("/")
def home():
    return {"message": "Backend is running!"}

@app.post("/submit-claim")
def submit_claim(claim: Claim):

    db: Session = SessionLocal()

    initial_state = {
        "claim": claim.text,
        "verification_report": {},
        "archivist_result": {},
        "investigation_round": 0,
        "max_rounds": 2,
        "trace": []
    }

    final_state = app_graph.invoke(initial_state)

    verification_report = final_state["verification_report"]

    archivist_result = final_state["archivist_result"]

    decision = archivist_result["decision"]

    investigation_round = final_state.get(
        "investigation_round",
        verification_report.get("investigation_round", 1)
    )
    max_rounds = final_state.get("max_rounds", 1)
    conflict_exhausted = (
        decision == "CONFLICT"
        and investigation_round >= max_rounds
    )

    verdict = verification_report.get("verdict", "DISPUTED")

    if decision == "REDUNDANT":

        archive_action = "ALREADY_ARCHIVED"

    elif decision == "SEMANTIC_DUPLICATE":

        archive_action = "DUPLICATE_DETECTED"

    elif decision == "CONFLICT":

        archive_action = "ESCALATED" if conflict_exhausted else "UNDER_REVIEW"

    else:

        archive_action = "ARCHIVED"

    if decision == "CONFLICT":

        if conflict_exhausted:
            verdict = "DISPUTED"

        contradiction_note = (
            f"Contradiction detected against archived entry: "
            f"{archivist_result.get('conflicting_claim', 'unknown')}."
        )
        analysis_steps = list(verification_report.get("analysis_steps", []))
        escalation_note = None

        analysis_steps.append(
            {
                "step": "archive_conflict",
                "detail": contradiction_note
            }
        )

        if conflict_exhausted:

            escalation_note = (
                "Escalated to human review after "
                f"{investigation_round} investigation rounds."
            )

            analysis_steps.append(
                {
                    "step": "escalation",
                    "detail": escalation_note
                }
            )

        verification_report["analysis_steps"] = analysis_steps

        current_confidence = verification_report["confidence"]
        verification_report["confidence"] = max(
            15,
            min(current_confidence - 20, 50)
        )

        verification_report["reason"] = (
            f"{verification_report['reason']} "
            f"Note: {contradiction_note}"
        )

    analysis_payload = {
        "verdict": verdict,
        "archive_action": archive_action,
        "confidence": verification_report["confidence"],
        "reason": verification_report["reason"],
        "sources": verification_report["sources"],
        "support_count": verification_report.get("support_count"),
        "contradiction_count": verification_report.get("contradiction_count"),
        "contradiction_detected": verification_report.get("contradiction_detected"),
        "source_assessment": verification_report.get("source_assessment", []),
        "credibility_breakdown": verification_report.get(
            "credibility_breakdown",
            {}
        ),
        "credibility_average": verification_report.get("credibility_average"),
        "analysis_steps": verification_report.get("analysis_steps", []),
        "cross_check": verification_report.get("cross_check", {}),
        "investigation_round": verification_report.get("investigation_round"),
        "trace": final_state.get("trace", [])
    }

    if decision == "REDUNDANT":

        return {
            "message": archivist_result["message"],
            "decision": decision,
            **analysis_payload
        }

    if decision == "SEMANTIC_DUPLICATE":

        return {
            "message": archivist_result["message"],
            "decision": decision,
            "matched_claim": archivist_result.get("matched_claim"),
            **analysis_payload
        }

    if decision == "CONFLICT":

        sources = ", ".join(verification_report["sources"])

        existing_review = (
            db.query(ReviewQueueRecord)
            .filter(ReviewQueueRecord.claim_text == claim.text)
            .first()
        )

        if existing_review:

            existing_review.decision = decision
            existing_review.message = archivist_result["message"]
            existing_review.verification_status = verdict
            existing_review.confidence_score = verification_report["confidence"]
            existing_review.verification_reason = verification_report["reason"]
            existing_review.sources = sources
            existing_review.status = "PENDING"

            db.commit()
            db.refresh(existing_review)

            queue_item = existing_review

        else:

            queue_item = ReviewQueueRecord(
                claim_text=claim.text,
                decision=decision,
                message=archivist_result["message"],
                verification_status=verdict,
                confidence_score=verification_report["confidence"],
                verification_reason=verification_report["reason"],
                sources=sources,
                status="PENDING"
            )

            db.add(queue_item)
            db.commit()
            db.refresh(queue_item)

        return {
            "message": archivist_result["message"],
            "decision": decision,
            "queued": True,
            "queue_id": queue_item.id,
            **analysis_payload
        }

    new_claim = ClaimRecord(
        claim_text=claim.text,
        verification_status=verdict,
        confidence_score=verification_report["confidence"],
        verification_reason=verification_report["reason"],
        sources=", ".join(verification_report["sources"])
    )

    db.add(new_claim)

    db.commit()

    db.refresh(new_claim)

    return {
        "message": "Claim verified and archived.",
        "decision": decision,
        "claim": new_claim.claim_text,
        **analysis_payload
    }


@app.get("/review-queue")
def get_review_queue():

    db: Session = SessionLocal()

    items = (
        db.query(ReviewQueueRecord)
        .order_by(ReviewQueueRecord.created_at.desc())
        .all()
    )

    results = []

    for item in items:

        sources = item.sources.split(", ") if item.sources else []

        results.append(
            {
                "id": item.id,
                "claim": item.claim_text,
                "decision": item.decision,
                "message": item.message,
                "status": item.status,
                "escalation_status": item.status,
                "verdict": item.verification_status,
                "confidence": item.confidence_score,
                "reason": item.verification_reason,
                "sources": sources,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at
                    else None
                )
            }
        )

    return {"items": results}