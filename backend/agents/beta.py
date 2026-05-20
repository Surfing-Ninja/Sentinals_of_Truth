from difflib import SequenceMatcher

from models import ClaimRecord


def semantic_similarity(text_a: str, text_b: str):

    return SequenceMatcher(None, text_a, text_b).ratio()


def archivist_decision(db, verification_report):

    existing_claims = db.query(ClaimRecord).all()
    existing_count = len(existing_claims)

    incoming_claim = verification_report["claim"].lower().strip()

    incoming_verdict = verification_report.get("verdict", "DISPUTED")

    for stored_claim in existing_claims:

        stored_text = stored_claim.claim_text.lower().strip()

        if incoming_claim == stored_text:

            return {
                "decision": "REDUNDANT",
                "message": "This claim already exists in the archive.",
                "decision_reason": "Exact duplicate found.",
                "existing_status": stored_claim.verification_status,
                "existing_count": existing_count
            }

        similarity = semantic_similarity(incoming_claim, stored_text)

        if similarity >= 0.85:

            return {
                "decision": "SEMANTIC_DUPLICATE",
                "message": f"A very similar claim already exists (similarity: {round(similarity * 100)}%).",
                "decision_reason": "Semantic near-duplicate detected via text similarity.",
                "matched_claim": stored_claim.claim_text,
                "existing_status": stored_claim.verification_status,
                "existing_count": existing_count
            }

        if similarity >= 0.55:

            stored_status = stored_claim.verification_status

            verdict_conflict = (
                (incoming_verdict == "SUPPORTED" and stored_status in ("FALSE", "DISPUTED"))
                or (incoming_verdict == "FALSE" and stored_status in ("SUPPORTED", "VERIFIED"))
            )

            if verdict_conflict:

                return {
                    "decision": "CONFLICT",
                    "message": (
                        f"This claim conflicts with an archived entry "
                        f"(archived verdict: {stored_status})."
                    ),
                    "decision_reason": "Verdict contradiction between incoming and archived claim.",
                    "conflicting_claim": stored_claim.claim_text,
                    "conflicting_status": stored_status,
                    "existing_count": existing_count
                }

    return {
        "decision": "INSERT",
        "message": "Claim verified and archived.",
        "decision_reason": "No duplicate or conflict detected.",
        "existing_count": existing_count
    }
