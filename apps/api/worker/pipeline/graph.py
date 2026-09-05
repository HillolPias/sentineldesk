from langgraph.graph import StateGraph, END

from worker.pipeline.state import TriageState
from worker.pipeline.nodes.classify import classify_node
from worker.pipeline.nodes.retrieve import retrieve_node
from worker.pipeline.nodes.draft import draft_node
from worker.pipeline.nodes.guardrail import guardrail_node


async def finalize_node(state: TriageState) -> dict:
    # Runs only after a human approves and the graph is resumed.
    # Placeholder for now — Step 9e will have the approval endpoint
    # trigger this by resuming the graph.
    return {"finalized": True}


def build_graph() -> StateGraph:
    graph = StateGraph(TriageState)

    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("draft", draft_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "guardrail")
    graph.add_edge("guardrail", "finalize")

    graph.add_edge("finalize", END)

    return graph


def compile_graph(checkpointer):
    return build_graph().compile(
        checkpointer=checkpointer, interrupt_after=["guardrail"]
    )
