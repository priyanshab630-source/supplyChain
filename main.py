import uuid
from pprint import pprint

from PROJECT.graph.run_graph import run_graph


def main():

    print("=" * 80)
    print("SUPPLY CHAIN MULTI-AGENT AI")
    print("=" * 80)

    # One thread_id per CLI session, so every question you ask in
    # this run shares conversation memory via the graph's
    # checkpointer (see graph/workflow.py). Restarting the CLI
    # starts a fresh conversation.
    thread_id = str(uuid.uuid4())

    while True:

        question = input("\nAsk a question (type 'exit' to quit): ")

        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:

            final_state = run_graph(question, thread_id=thread_id)

            print("\n" + "=" * 80)
            print("FINAL STATE")
            print("=" * 80)

            pprint(final_state)

            print("\n" + "=" * 80)
            print("AGENT RESULTS")
            print("=" * 80)

            if final_state.get("inventory"):
                print("\nInventory")
                print(final_state["inventory"])

            if final_state.get("forecast"):
                print("\nForecast")
                print(final_state["forecast"])

            if final_state.get("supplier"):
                print("\nSupplier")
                print(final_state["supplier"])

            if final_state.get("kg"):
                print("\nKnowledge Graph")
                print(final_state["kg"])

            if final_state.get("network_results"):
                print("\nNetwork Results")
                print(final_state["network_results"])

            if final_state.get("risk"):
                print("\nRisk")
                print(final_state["risk"])

            if final_state.get("recommendation"):
                print("\nRecommendation")
                print(final_state["recommendation"])

            # ------------------------------------------------------
            # ANSWER prints AFTER AGENT RESULTS - so you see the raw
            # per-agent data (including any error a node hit) before
            # the synthesized answer, instead of the answer showing
            # up first with no supporting context above it.
            # ------------------------------------------------------
            print("\n" + "=" * 80)
            print("ANSWER")
            print("=" * 80)

            if final_state.get("final_answer"):
                print(final_state["final_answer"])
            else:
                print("No answer was generated.")

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
