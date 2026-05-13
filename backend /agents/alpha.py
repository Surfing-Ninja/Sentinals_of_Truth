import os
from urllib.parse import urlparse

import requests

from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

HIGH_TRUST_DOMAINS = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "britannica.com"
]

BLOG_DOMAINS = [
    "medium.com",
    "substack.com",
    "wordpress.com",
    "blogspot.com"
]

KNOWN_FALSEHOODS = [
    "moon made of cheese",
    "flat earth",
    "earth is flat",
    "5g causes covid",
    "aliens elected prime minister"
]

CONTRADICTION_KEYWORDS = [
    "debunk",
    "false",
    "hoax",
    "myth",
    "not true",
    "fake",
    "misinformation",
    "no evidence",
    "fact check",
    "factcheck",
    "incorrect",
    "misleading"
]


def search_claim_online(
    claim_text: str,
    max_results: int = 3,
    search_depth: str = "basic"
):

    if not TAVILY_API_KEY:

        return {"results": [], "error": "missing_api_key"}

    url = "https://api.tavily.com/search"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": claim_text,
        "search_depth": search_depth,
        "max_results": max_results
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        if not response.ok:

            return {
                "results": [],
                "error": f"tavily_status_{response.status_code}"
            }

        return response.json()

    except requests.RequestException:

        return {"results": [], "error": "tavily_request_failed"}


def normalize_domain(url: str):

    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):

        domain = domain[4:]

    return domain


def domain_matches(domain: str, entries: list[str]):

    return any(domain == entry or domain.endswith(f".{entry}") for entry in entries)


def score_source(url: str):

    if not url:

        return 40, "low"

    domain = normalize_domain(url)

    if domain.endswith(".gov") or ".gov." in domain:

        score = 95

    elif domain.endswith(".edu") or ".edu." in domain:

        score = 90

    elif domain_matches(domain, HIGH_TRUST_DOMAINS):

        score = 80

    elif "wikipedia.org" in domain:

        score = 70

    elif domain_matches(domain, BLOG_DOMAINS) or "blog" in domain:

        score = 50

    else:

        score = 40

    if score >= 90:

        label = "high"

    elif score >= 70:

        label = "medium"

    else:

        label = "low"

    return score, label


def analyze_evidence(results):

    sources = []
    assessment = []
    scores = []
    breakdown = {"high": 0, "medium": 0, "low": 0}

    for item in results:

        url = item.get("url")

        if not url:

            continue

        credibility_score, credibility_label = score_source(url)

        sources.append(url)
        scores.append(credibility_score)

        assessment.append(
            {
                "url": url,
                "credibility": credibility_score,
                "label": credibility_label
            }
        )

        breakdown[credibility_label] += 1

    return sources, assessment, breakdown, scores


def cross_check_sources(breakdown, total_sources):

    if total_sources == 0:

        return {
            "consensus": "none",
            "notes": "No sources to cross-check."
        }

    if breakdown["high"] >= 2:

        return {
            "consensus": "strong",
            "notes": "Multiple high-credibility sources support the claim."
        }

    if breakdown["high"] >= 1 and breakdown["medium"] >= 1:

        return {
            "consensus": "moderate",
            "notes": "Mixed high/medium sources support the claim."
        }

    if breakdown["high"] == 0 and breakdown["medium"] >= 2:

        return {
            "consensus": "moderate",
            "notes": "Multiple medium-credibility sources support the claim."
        }

    if breakdown["high"] == 0 and breakdown["medium"] == 0:

        return {
            "consensus": "weak",
            "notes": "Only low-credibility sources were found."
        }

    return {
        "consensus": "weak",
        "notes": "Limited evidence for cross-checking."
    }


def compute_confidence(scores, total_sources, breakdown, support_count, contradiction_count):

    if total_sources == 0:

        return 15

    average = sum(scores) / total_sources
    score = average + min(total_sources * 5, 20)

    if support_count >= 2:

        score += 20

    if contradiction_count == 0:

        score += 15

    trusted_count = breakdown["high"] + breakdown["medium"]

    if trusted_count >= 2:

        score += 20

    elif trusted_count == 1:

        score += 10

    if breakdown["low"] == total_sources:

        score -= 10

    if contradiction_count > 0:

        score -= 40

    if total_sources == 1:

        score -= 10

    return max(15, min(95, round(score)))


def extract_result_text(item):

    parts = [
        item.get("title"),
        item.get("content"),
        item.get("snippet"),
        item.get("description")
    ]

    return " ".join([part for part in parts if part]).lower()


def is_contradiction(item):

    text = extract_result_text(item)

    return any(keyword in text for keyword in CONTRADICTION_KEYWORDS)


def count_support(results):

    return sum(1 for item in results if not is_contradiction(item))


def count_contradictions(results):

    return sum(1 for item in results if is_contradiction(item))


def detect_known_falsehood(claim_text: str):

    lower_claim = claim_text.lower()

    for pattern in KNOWN_FALSEHOODS:

        if pattern in lower_claim:

            return pattern

    return None


def investigate_claim(claim_text: str, investigation_round: int = 1):

    falsehood_match = detect_known_falsehood(claim_text)

    if falsehood_match:

        return {
            "claim": claim_text,
            "verified": False,
            "verdict": "FAKE",
            "confidence": 15,
            "reason": "Known misinformation pattern detected.",
            "sources": [],
            "support_count": 0,
            "contradiction_count": 1,
            "analysis_steps": [
                {
                    "step": "contradiction",
                    "detail": f"Matched falsehood pattern: {falsehood_match}."
                }
            ],
            "credibility_breakdown": {
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "credibility_average": 0,
            "source_assessment": [],
            "cross_check": {
                "consensus": "none",
                "notes": "No sources collected for known falsehood."
            },
            "contradiction_detected": True,
            "investigation_round": investigation_round
        }

    max_results = 3 if investigation_round <= 1 else 5

    search_results = search_claim_online(
        claim_text,
        max_results=max_results
    )

    results = search_results.get("results", [])

    if search_results.get("error"):

        return {
            "claim": claim_text,
            "verified": False,
            "verdict": "DISPUTED",
            "confidence": 15,
            "reason": "Search failed or API key missing.",
            "sources": [],
            "support_count": 0,
            "contradiction_count": 0,
            "analysis_steps": [
                {
                    "step": "search",
                    "detail": "Tavily search failed or API key is missing."
                }
            ],
            "credibility_breakdown": {
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "credibility_average": 0,
            "source_assessment": [],
            "cross_check": {
                "consensus": "none",
                "notes": "No results to cross-check."
            },
            "contradiction_detected": False,
            "investigation_round": investigation_round
        }

    contradiction_query = f"{claim_text} debunked"
    contradiction_results = []

    contradiction_search = search_claim_online(
        contradiction_query,
        max_results=3
    )

    if not contradiction_search.get("error"):

        contradiction_results = contradiction_search.get("results", [])

    sources, assessment, breakdown, scores = analyze_evidence(results)

    total_sources = len(sources)

    credibility_average = (
        round(sum(scores) / total_sources, 1)
        if total_sources
        else 0
    )

    cross_check = cross_check_sources(breakdown, total_sources)

    support_count = count_support(results)
    contradiction_count = (
        count_contradictions(results)
        + count_contradictions(contradiction_results)
    )
    contradiction_detected = contradiction_count > 0

    confidence = compute_confidence(
        scores,
        total_sources,
        breakdown,
        support_count,
        contradiction_count
    )

    if contradiction_detected:

        verdict = "FAKE" if support_count == 0 else "DISPUTED"

    else:

        verdict = "VERIFIED" if confidence >= 70 else "DISPUTED"

    verified = verdict == "VERIFIED"

    steps = [
        {
            "step": "search",
            "detail": f"Collected {total_sources} sources from Tavily."
        },
        {
            "step": "contradiction_search",
            "detail": (
                "Debunk query returned "
                f"{len(contradiction_results)} results."
            )
        },
        {
            "step": "analyze",
            "detail": (
                "Credibility breakdown - "
                f"high: {breakdown['high']}, "
                f"medium: {breakdown['medium']}, "
                f"low: {breakdown['low']}, "
                f"average score: {credibility_average}."
            )
        },
        {
            "step": "cross_check",
            "detail": cross_check["notes"]
        },
        {
            "step": "consensus",
            "detail": (
                "Support signals: "
                f"{support_count}. Contradictions: {contradiction_count}."
            )
        },
        {
            "step": "confidence",
            "detail": f"Confidence set to {confidence} from {total_sources} sources."
        }
    ]

    if verdict == "VERIFIED":

        reason = "Supporting sources discovered online."

    elif contradiction_detected:

        reason = "Contradictory evidence detected during debunk search."

    else:

        reason = "Evidence is weak or mixed."

    return {
        "claim": claim_text,
        "verified": verified,
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "sources": sources,
        "support_count": support_count,
        "contradiction_count": contradiction_count,
        "analysis_steps": steps,
        "credibility_breakdown": breakdown,
        "credibility_average": credibility_average,
        "source_assessment": assessment,
        "cross_check": cross_check,
        "contradiction_detected": contradiction_detected,
        "investigation_round": investigation_round
    }
