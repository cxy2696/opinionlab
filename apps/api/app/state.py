"""Run state machine with the cancelling intermediate state ()."""

from __future__ import annotations

STATUSES = {
    "draft",
    "queued",
    "running",
    "cancelling",
    "cancelled",
    "succeeded",
    "failed",
    "partial",
}
TERMINAL = {"cancelled", "succeeded", "failed", "partial"}
ALLOWED: dict[str, set[str]] = {
    "draft": {"queued"},
    "queued": {"running", "cancelling"},
    "running": {"succeeded", "failed", "partial", "cancelling"},
    "cancelling": {"cancelled"},
}


class InvalidTransition(ValueError):
    pass


def transition(current: str, target: str) -> str:
    """Validate a state change; queued -> cancelled directly is forbidden."""
    if current in TERMINAL:
        raise InvalidTransition(f"{current} is terminal")
    if target not in ALLOWED.get(current, set()):
        raise InvalidTransition(f"cannot go from {current} to {target}")
    return target


def request_cancel(current: str, done_replicas: int, repeats: int) -> tuple[str, bool]:
    """Enter ``cancelling`` without dropping already-finished replicas."""
    if current in TERMINAL:
        return current, False
    if current == "queued":
        return "cancelling", True
    if current == "running":
        # replicas already produced are preserved; the worker finalises to cancelled
        assert 0 <= done_replicas <= repeats
        return "cancelling", True
    return current, False


def finalize_cancel(current: str) -> str:
    if current != "cancelling":
        raise InvalidTransition("only cancelling runs can be finalised")
    return transition(current, "cancelled")


def reconcile_status(done_replicas: int, repeats: int, current: str) -> str | None:
    """Return the corrected status when counters disagree, else None."""
    if done_replicas == repeats and current not in TERMINAL:
        return "succeeded"
    if done_replicas > 0 and done_replicas < repeats and current in TERMINAL:
        return "partial"
    return None
