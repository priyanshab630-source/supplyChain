"""
Custom middleware: logs every tool call (name, args, success/failure,
duration) to event_log - the same table P5's simulator writes to.

Why this AND LangSmith: LangSmith is the right place to debug/inspect
a specific run interactively, but it's an external service you query
through its UI/API. event_log is queryable directly from YOUR
database with plain SQL, persists as long as your DB does, and is
already what P8's eval framework and P5's simulator both read/write
- this keeps tool-call auditing in the same place instead of only
existing in a third-party dashboard.
"""

import time

from langchain.agents.middleware import wrap_tool_call

from PROJECT.data_loader.loader import write_event_log


@wrap_tool_call
def tool_call_audit_middleware(request, handler):
    tool_name = request.tool_call.get("name", "unknown_tool")
    tool_args = request.tool_call.get("args", {})

    started_at = time.time()

    try:
        result = handler(request)
        duration_ms = round((time.time() - started_at) * 1000, 1)

        _log_call(tool_name, tool_args, duration_ms, success=True, error=None)
        return result

    except Exception as exc:
        duration_ms = round((time.time() - started_at) * 1000, 1)
        _log_call(tool_name, tool_args, duration_ms, success=False, error=str(exc))
        raise  # don't swallow the error - just log it, then let it propagate normally


def _log_call(tool_name, tool_args, duration_ms, success, error):
    try:
        write_event_log(
            "tool_call",
            {
                "tool_name": tool_name,
                "args": tool_args,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
            },
        )
    except Exception as exc:
        # Logging failures should never break the actual tool call.
        print(f"[AUDIT] Warning: failed to log tool call: {exc}")