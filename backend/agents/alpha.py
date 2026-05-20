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
    "britannica.com",
    "nasa.gov",
    "isro.gov.in",
    "who.int",
    "un.org",
    "nature.com",
    "sciencedirect.com",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "aljazeera.com",
]

MEDIUM_TRUST_DOMAINS = [
    "wikipedia.org",
    "hindustantimes.com",
    "ndtv.com",
    "timesofindia.indiatimes.com",
    "thehindu.com",
    "livemint.com",
    "economictimes.indiatimes.com",
    "scroll.in",
    "firstpost.com",
    "news18.com",
    "cnbc.com",
    "cnn.com",
    "foxnews.com",
    "nbcnews.com",
]

BLOG_DOMAINS = [
    "medium.com",
    "substack.com",
    "wordpress.com",
    "blogspot.com",
]

LOW_TRUST_DOMAINS = [
    "reddit.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "quora.com",
    "pinterest.com",
    "tumblr.com",
]

YOUTUBE_DOMAINS = [
    "youtube.com",
    "youtu.be",
]

KNOWN_FALSEHOODS = [
    "moon made of cheese",
    "flat earth",
    "earth is flat",
    "5g causes covid",
    "aliens elected prime minister",
    "vaccines cause autism",
    "birds aren't real",
]

CONTRADICTION_KEYWORDS = [
    "hoax",
    "myth",
    "not true",
    "fake",
    "misinformation",
    "no evidence",
    "incorrect",
    "misleading",
    "conspiracy",
    "disproven",
    "baseless",
    "unfounded",
]

NEUTRALIZER_PATTERNS = [
    "debunked",
    "debunk",
    "fact check",
    "factcheck",
    "claims are false",
    "claims are misleading",
    "is not true that",
    "proven false",
    "ruled false",
]

CONFIRMATION_KEYWORDS = [
    "confirmed",
    "successfully",
    "achieved",
    "accomplished",
    "landed",
    "launched",
    "announced",
    "official",
    "historic",
    "milestone",
    "breakthrough",
    "approved",
    "verified",
    "established",
]


def search_claim_online(
    claim_text: str,
    max_results: int = 5,
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

        return 30, "low"

    domain = normalize_domain(url)

    if domain.endswith(".gov") or ".gov." in domain:

        score = 92

    elif domain.endswith(".edu") or ".edu." in domain:

        score = 88

    elif domain.endswith(".org") and not domain_matches(domain, LOW_TRUST_DOMAINS):

        score = 75

    elif domain_matches(domain, HIGH_TRUST_DOMAINS):

        score = 85

    elif domain_matches(domain, MEDIUM_TRUST_DOMAINS):

        score = 72

    elif domain_matches(domain, YOUTUBE_DOMAINS):

        score = 35

    elif domain_matches(domain, LOW_TRUST_DOMAINS):

        score = 25

    elif domain_matches(domain, BLOG_DOMAINS) or "blog" in domain:

        score = 45

    else:

        score = 55

    if score >= 80:

        label = "high"

    elif score >= 60:

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
            "notes": "Multiple high-credibility sources agree on the claim."
        }

    if breakdown["high"] >= 1 and breakdown["medium"] >= 1:

        return {
            "consensus": "moderate",
            "notes": "Mix of high and medium credibility sources support the claim."
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

        return 10

    average = sum(scores) / total_sources

    base_score = average * 0.5

    source_bonus = min(total_sources * 4, 15)

    if support_count >= 3:

        support_bonus = 25

    elif support_count >= 2:

        support_bonus = 18

    elif support_count >= 1:

        support_bonus = 10

    else:

        support_bonus = 0

    trusted_count = breakdown["high"] + breakdown["medium"]

    if trusted_count >= 3:

        trust_bonus = 22

    elif trusted_count >= 2:

        trust_bonus = 16

    elif trusted_count == 1:

        trust_bonus = 8

    else:

        trust_bonus = 0

    if contradiction_count == 0 and support_count >= 1:

        consistency_bonus = 10

    elif contradiction_count == 0:

        consistency_bonus = 5

    else:

        consistency_bonus = 0

    score = base_score + source_bonus + support_bonus + trust_bonus + consistency_bonus

    if breakdown["low"] == total_sources:

        score -= 15

    if contradiction_count > 0:

        penalty = min(contradiction_count * 15, 40)
        score -= penalty

    if total_sources == 1:

        score -= 8

    return max(10, min(95, round(score)))


def extract_result_text(item):

    parts = [
        item.get("title"),
        item.get("content"),
        item.get("snippet"),
        item.get("description")
    ]

    return " ".join([part for part in parts if part]).lower()


def text_has_confirmation(text):

    return any(keyword in text for keyword in CONFIRMATION_KEYWORDS)


def text_has_contradiction(text):

    return any(keyword in text for keyword in CONTRADICTION_KEYWORDS)


def is_contradiction(item):

    text = extract_result_text(item)

    has_negative = text_has_contradiction(text)
    has_positive = text_has_confirmation(text)

    has_neutralizer = any(pattern in text for pattern in NEUTRALIZER_PATTERNS)

    if has_neutralizer:

        return False

    if has_negative and has_positive:

        return False

    return has_negative


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


def build_reason(verdict, support_count, contradiction_count, breakdown, total_sources, credibility_average):

    trusted_count = breakdown["high"] + breakdown["medium"]

    if verdict == "SUPPORTED":

        if trusted_count >= 2:
            return f"Multiple reliable sources ({trusted_count} high/medium credibility) confirm this claim."
        elif trusted_count == 1:
            return f"Claim supported by {support_count} source(s), including trusted outlets."
        else:
            return f"Claim supported by {support_count} source(s) with average credibility of {credibility_average}."

    elif verdict == "FALSE":

        return "Evidence contradicts this claim across multiple sources."

    elif verdict == "DISPUTED":

        if contradiction_count > 0 and support_count > 0:
            return f"Mixed evidence: {support_count} supporting and {contradiction_count} contradicting source(s) found."
        elif contradiction_count > 0:
            return f"Contradictory evidence found in {contradiction_count} source(s)."
        else:
            return "Evidence is inconclusive with mixed source credibility."

    elif verdict == "INSUFFICIENT_EVIDENCE":

        if total_sources == 0:
            return "No sources found to verify this claim."
        else:
            return f"Only {total_sources} low-quality source(s) found. Insufficient evidence to make a determination."

    return "Unable to determine claim veracity."


def investigate_claim(claim_text: str, investigation_round: int = 1):

    falsehood_match = detect_known_falsehood(claim_text)

    if falsehood_match:

        return {
            "claim": claim_text,
            "verified": False,
            "verdict": "FALSE",
            "confidence": 92,
            "reason": f"Known misinformation pattern detected: '{falsehood_match}'.",
            "sources": [],
            "support_count": 0,
            "contradiction_count": 1,
            "analysis_steps": [
                {
                    "step": "pattern_match",
                    "detail": f"Matched known falsehood pattern: '{falsehood_match}'."
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
                "notes": "No external sources needed for known falsehood."
            },
            "contradiction_detected": True,
            "investigation_round": investigation_round
        }

    max_results = 5 if investigation_round <= 1 else 7

    search_results = search_claim_online(
        claim_text,
        max_results=max_results
    )

    results = search_results.get("results", [])

    if search_results.get("error"):

        return {
            "claim": claim_text,
            "verified": False,
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 10,
            "reason": "Source retrieval failed. Unable to verify.",
            "sources": [],
            "support_count": 0,
            "contradiction_count": 0,
            "analysis_steps": [
                {
                    "step": "retrieval",
                    "detail": "Source retrieval failed or API key is missing."
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

    contradiction_query = f"{claim_text} debunked OR false OR hoax"
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

    if total_sources == 0:

        verdict = "INSUFFICIENT_EVIDENCE"

    elif contradiction_detected and support_count == 0:

        verdict = "FALSE"

    elif contradiction_detected and support_count > 0:

        if contradiction_count > support_count:
            verdict = "FALSE" if confidence < 35 else "DISPUTED"
        else:
            verdict = "DISPUTED" if confidence < 70 else "SUPPORTED"

    elif support_count >= 2 and confidence >= 65:

        verdict = "SUPPORTED"

    elif confidence >= 70:

        verdict = "SUPPORTED"

    elif confidence >= 40:

        verdict = "DISPUTED"

    elif breakdown["low"] == total_sources and total_sources <= 2:

        verdict = "INSUFFICIENT_EVIDENCE"

    else:

        verdict = "DISPUTED"

    verified = verdict == "SUPPORTED"

    reason = build_reason(
        verdict,
        support_count,
        contradiction_count,
        breakdown,
        total_sources,
        credibility_average
    )

    steps = [
        {
            "step": "retrieval",
            "detail": f"Retrieved {total_sources} sources via web search."
        },
        {
            "step": "credibility_analysis",
            "detail": (
                "Source credibility breakdown — "
                f"high: {breakdown['high']}, "
                f"medium: {breakdown['medium']}, "
                f"low: {breakdown['low']}. "
                f"Average credibility: {credibility_average}."
            )
        },
        {
            "step": "contradiction_scan",
            "detail": (
                f"Scanned {len(contradiction_results)} debunk results. "
                f"Found {contradiction_count} contradiction signal(s)."
            )
        },
        {
            "step": "cross_check",
            "detail": cross_check["notes"]
        },
        {
            "step": "consensus",
            "detail": (
                f"Supporting signals: {support_count}. "
                f"Contradicting signals: {contradiction_count}."
            )
        },
        {
            "step": "verdict",
            "detail": f"Verdict: {verdict} (confidence {confidence}/100)."
        }
    ]

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
