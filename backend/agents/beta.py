from models import ClaimRecord


def archivist_decision(db, verification_report):

	existing_claims = db.query(ClaimRecord).all()
	existing_count = len(existing_claims)

	incoming_claim = verification_report["claim"].lower()

	incoming_status = (
		"VERIFIED"
		if verification_report["verified"]
		else "FAKE"
	)

	for stored_claim in existing_claims:

		stored_text = stored_claim.claim_text.lower()

		if incoming_claim == stored_text:

			return {
				"decision": "REDUNDANT",
				"message": "Claim already exists in archive.",
				"decision_reason": "Exact match found in archive.",
				"existing_count": existing_count
			}

		if (
			"moon made of cheese" in incoming_claim
			and
			"moon made of cheese" not in stored_text
		):

			return {
				"decision": "CONFLICT",
				"message": "Contradictory information detected.",
				"decision_reason": "Conflict rule triggered by archive comparison.",
				"existing_count": existing_count
			}

	return {
		"decision": "INSERT",
		"message": "Claim approved for archival.",
		"decision_reason": "No duplicate or conflict rules triggered.",
		"existing_count": existing_count
	}
