"""
Custom middleware: normalizes any tool call's `tank_id` argument
(e.g. "1" -> "Tank 1") automatically, BEFORE the tool body runs.

Previously this was a copy-pasted two-line block inside every tool
function individually (inventory_risk_tool, forecast_tool) - correct,
but relying on every future tool remembering to paste it too. This
makes it structural instead: ANY tool registered with this middleware
gets normalized tank_id args for free, whether or not its own
function body calls normalize_tank_id.

Tools can (and should) still call normalize_tank_id() directly too if
they're also invoked outside the create_agent loop (e.g. nodes.py
calling inventory_engine.run_for_tank(state["tank_id"]) directly) -
this middleware only runs for calls that go through the agent's tool-
calling loop.
"""

from langchain.agents.middleware import wrap_tool_call

from PROJECT.tools.tank_id_utils import normalize_tank_id


@wrap_tool_call
def tank_id_normalizer_middleware(request, handler):
    tool_args = request.tool_call.get("args", {}) or {}

    if "tank_id" in tool_args and tool_args["tank_id"]:
        tool_args["tank_id"] = normalize_tank_id(tool_args["tank_id"])

    return handler(request)