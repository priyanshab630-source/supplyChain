class GuardrailViolation(Exception):
    """
    Raised when a hard guardrail check fails - callers should treat
    this as a blocking error, not a warning. It's a plain Exception
    on purpose, not a special type node-level try/except blocks need
    to know about: every node in nodes.py already wraps its agent
    call in try/except Exception and turns it into an error string,
    so a GuardrailViolation surfaces through that SAME existing path
    with no new error-handling code needed anywhere.
    """

    def __init__(self, guardrail_name: str, reason: str):
        self.guardrail_name = guardrail_name
        self.reason = reason
        super().__init__(f"[{guardrail_name}] {reason}")