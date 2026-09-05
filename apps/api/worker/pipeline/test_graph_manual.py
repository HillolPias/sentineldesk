import asyncio
import sys
import uuid
from worker.pipeline.checkpointer import get_checkpointer
from worker.pipeline.graph import compile_graph


async def test():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with get_checkpointer() as checkpointer:
        graph = compile_graph(checkpointer)

        initial_state = {
            "ticket_id": thread_id,
            "subject": "Cant log in",
            "body": "I keep getting an error when I try to log in, urgent",
        }

        print("--- First invoke (should stop after guardrail) ---")
        result = await graph.ainvoke(initial_state, config=config)
        print("State after first invoke:", result)

        snapshot = await graph.aget_state(config)
        print("Nodes still pending:", snapshot.next)

        print(
            "\n--- Resuming (simulates a human clicking approve, later, in a different process) ---"
        )
        resumed = await graph.ainvoke(None, config=config)
        print("State after resume:", resumed)

        final_snapshot = await graph.aget_state(config)
        print("Nodes still pending after resume:", final_snapshot.next)


def main():
    if sys.platform == "win32":
        asyncio.run(test(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(test())


if __name__ == "__main__":
    main()
