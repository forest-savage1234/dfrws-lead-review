"""Fixture actions. Expected outcomes never enter the engine or runner."""
from .model import ReviewError, canonical

def resolve_refs(ledger, refs):
    out = []
    for ref in refs:
        node_id = ledger.observation(ref["observation_key"])["id"] if "observation_key" in ref else ref["node_id"]
        out.append({"node_id": node_id, "fields": ref["fields"]})
    return out

def execute(ledger, action):
    args = {k: v for k, v in action.items() if k not in {"op", "event"}}
    op = action["op"]
    if op == "document":
        return ledger.document(**args)
    if op == "capture":
        value = args.pop("content", None)
        raw = args.pop("raw", None)
        args["content"] = raw.encode("utf-8") if raw is not None else canonical(value).encode("utf-8")
        return ledger.capture(**args)
    if op in {"hypothesis", "decision"}:
        args["refs"] = resolve_refs(ledger, args["refs"])
        return getattr(ledger, op)(**args)
    if op == "human_review":
        decision_id = args.pop("decision_id")
        matching = [r for r in ledger.state()["review_requests"]
                    if r["decision_id"] == decision_id and r["status"] == "awaiting_human_review"]
        if not matching:
            raise ReviewError("No open request for this decision.")
        args["request_id"] = matching[-1]["id"]
        args["refs"] = resolve_refs(ledger, args["refs"])
        return ledger.review(**args)
    raise ReviewError("Unknown fixture operation: " + str(op))

def run_case(ledger, case):
    for action in case["setup"]:
        execute(ledger, action)
    before = ledger.state()
    events = []
    for action in case["actions"]:
        old_requests = {r["id"] for r in ledger.state()["review_requests"]}
        active = [d["id"] for d in ledger.active_decisions()]
        result = execute(ledger, action)
        state = ledger.state()
        new_requests = [r for r in state["review_requests"] if r["id"] not in old_requests]
        coverage = result.get("coverage", state["coverage"]) if isinstance(result, dict) else state["coverage"]
        broadcast = active if isinstance(result, dict) and result.get("source_changed") and not result.get("replayed") else []
        events.append({"event": action["event"], "op": action["op"], "result": result,
                       "new_requests": new_requests, "coverage": coverage,
                       "hash_broadcast_decisions": broadcast})
    return {"case_id": case["id"], "before": before, "events": events, "after": ledger.state()}
