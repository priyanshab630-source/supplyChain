import webbrowser

from PROJECT.graph.workflow import graph

png = graph.get_graph().draw_mermaid_png()

with open("workflow.png", "wb") as f:
    f.write(png)

webbrowser.open("workflow.png")

print("Workflow graph generated successfully.")

print()