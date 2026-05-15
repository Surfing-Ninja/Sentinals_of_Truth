from datetime import datetime
from typing import TypedDict

from agents.alpha import investigate_claim
from agents.beta import archivist_decision
from database import SessionLocal
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    claim: str
    verification_report: dict
    archivist_result: dict
    investigation_round: int
    max_rounds: int
    trace: list


def append_trace(state: AgentState, agent: str, action: str, detail: str):

    trace = state.get("trace", [])

    trace.append(
        {
            "timestamp": f"{datetime.utcnow().isoformat()}Z",
            "agent": agent,
            "action": action,
            "detail": detail
        }
    )

    state["trace"] = trace


def alpha_node(state: AgentState):
    state["investigation_round"] = state.get("investigation_round", 0) + 1

    append_trace(
        state,
        "AgentAlpha",
        "start",
        f"Investigation round {state['investigation_round']} initiated."
    )

    report = investigate_claim(
        state["claim"],
        investigation_round=state["investigation_round"]
    )

    state["verification_report"] = report

    sources_count = len(report.get("sources", []))
    append_trace(
        state,
        "AgentAlpha",
        "sources_collected",
        f"Gathered {sources_count} sources."
    )

    append_trace(
        state,
        "AgentAlpha",
        "confidence",
        f"Confidence set to {report.get('confidence')}."
    )

    return state


def beta_node(state: AgentState):

    db = SessionLocal()

    append_trace(
        state,
        "AgentBeta",
        "start",
        "Checking archive for duplicates or conflicts."
    )

    result = archivist_decision(
        db,
        state["verification_report"]
    )

    state["archivist_result"] = result

    existing_count = result.get("existing_count")
    if existing_count is not None:

        append_trace(
            state,
            "AgentBeta",
            "archive_scan",
            f"Scanned {existing_count} archived claims."
        )

    append_trace(
        state,
        "AgentBeta",
        "decision",
        f"Decision {result.get('decision')}: {result.get('message')}"
    )

    return state


def route_after_beta(state: AgentState):

    decision = state["archivist_result"].get("decision")

    if (
        decision == "CONFLICT"
        and state.get("investigation_round", 1) < state.get("max_rounds", 1)
    ):

        return "reinvestigate"

    return "end"


workflow = StateGraph(AgentState)

workflow.add_node("AgentAlpha", alpha_node)

workflow.add_node("AgentBeta", beta_node)

workflow.set_entry_point("AgentAlpha")

workflow.add_edge("AgentAlpha", "AgentBeta")

workflow.add_conditional_edges(
    "AgentBeta",
    route_after_beta,
    {
        "reinvestigate": "AgentAlpha",
        "end": END
    }
)

app_graph = workflow.compile()
