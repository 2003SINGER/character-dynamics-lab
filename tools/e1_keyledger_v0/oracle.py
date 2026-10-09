"""Independent finite-domain E1 reachability oracles.

The two searches below own their transition rules.  They intentionally do not
import an E1/E0 executor, planner, policy, or transition helper.  Their state
is an evaluator-side summary of all future-relevant physical, local-knowledge,
clock, scheduler, request, offer, and witness information; a returned path is
a prediction and is never written back into the input checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import heapq
import json
import time
from typing import Any


_MAX_T = 10
_INFINITY = 10**9


@dataclass(frozen=True)
class _State:
    t: int
    deadline: int
    holders: tuple[tuple[str, str | None], ...]
    intact_key1: bool
    destroyed_key1: bool
    key1_beneficial_owner_b: bool
    archive_open: bool
    ledger_intact: bool
    ledger_destroyed: bool
    ledger_beneficial_owner_archive: bool
    payment_beneficial_owner_a: bool
    tool_beneficial_owner_b: bool
    same_place: bool
    session: str
    offer_id: str | None
    offer_reply_time: int | None
    used: tuple[tuple[str, bool], ...]
    a_knows_key1: bool
    a_knows_ledger: bool
    a_knows_payment: bool
    b_knows_key1: bool
    b_knows_key1_destroyed: bool
    b_knows_payment: bool
    b_observes_tool_holder_a: bool
    b_observes_tool_holder_b: bool
    b_knows_toolB: bool
    b_observes_key1_held_by_b: bool
    b_observes_payment_held_by_b: bool
    b_saw_accept_reply: bool
    b_request_sent: bool
    b_request_provenance: str
    next_event_number: int
    next_action_number: int
    world_request_used: bool
    initial_b_slot_pending: bool
    witnessed: bool

    def holder(self, item: str) -> str | None:
        return dict(self.holders)[item]

    def with_holder(self, item: str, value: str | None) -> "_State":
        values = dict(self.holders)
        values[item] = value
        return replace(self, holders=tuple(sorted(values.items())))

    def used_bit(self, name: str) -> bool:
        return dict(self.used).get(name, False)

    def with_used(self, name: str) -> "_State":
        values = dict(self.used)
        values[name] = True
        return replace(self, used=tuple(sorted(values.items())))


def _has_entity(obs: dict[str, Any], entity_id: str) -> bool:
    return entity_id in obs.get("known_entities", [])


def _has_fact(obs: dict[str, Any], fact: str) -> bool:
    return fact in obs.get("known_facts", [])


def _sealed_witness(checkpoint: dict[str, Any], deadline: int) -> bool:
    """Validate a pre-existing acquisition from committed source evidence."""
    producer = checkpoint["domain"]["producer_version"]
    contiguous, frontier = 0, -1
    for seal in checkpoint.get("seals", []):
        if (seal.get("producer_version") != producer
                or seal.get("sealed_through") != contiguous + 1
                or not isinstance(seal.get("sequence_frontier"), int)
                or seal["sequence_frontier"] < frontier):
            break
        contiguous = seal["sealed_through"]
        frontier = seal["sequence_frontier"]
    receipts = checkpoint.get("receipts", [])
    actions = checkpoint.get("action_history", [])
    for event in checkpoint.get("events", []):
        at, seq = event.get("time"), event.get("sequence")
        if (event.get("event_type") != "ledger_acquired"
                or event.get("typed_args") != {"event": "ledger_acquired", "actor": "A", "item": "ledger"}
                or event.get("producer_version") != producer
                or not isinstance(at, int) or not 2 <= at <= deadline
                or not isinstance(seq, int) or at > contiguous or seq > frontier):
            continue
        for receipt in receipts:
            intent = receipt.get("intent", {})
            delta = receipt.get("delta_w", {})
            holder_delta = delta.get("holders")
            start = receipt.get("start_time")
            history_match = any(
                row.get("action_id") == receipt.get("action_id")
                and row.get("receipt_id") == receipt.get("receipt_id")
                and row.get("status") == "SUCCESS" and row.get("time") == start
                and row.get("intent") == intent
                for row in actions)
            if (receipt.get("producer_version") == producer
                    and receipt.get("accepted") is True
                    and receipt.get("status") == "SUCCESS"
                    and receipt.get("outcome") == "COMPLETED"
                    and isinstance(start, int) and receipt.get("end_time") == start + 1
                    and receipt.get("end_time") == at
                    and receipt.get("event_ids") == [event.get("event_id")]
                    and receipt.get("event_payloads") == [event]
                    and intent == {"operator": "take_ledger", "actor": "A", "args": {"item": "ledger"}}
                    and isinstance(holder_delta, list) and len(holder_delta) == 2
                    and isinstance(holder_delta[0], dict) and isinstance(holder_delta[1], dict)
                    and holder_delta[0].get("ledger") == "ARCHIVE"
                    and holder_delta[1].get("ledger") == "A"
                    and history_match):
                return True
    return False


def _initial(checkpoint: dict[str, Any]) -> _State:
    w = checkpoint["W"]
    oa, ob = checkpoint["O"]["A"], checkpoint["O"]["B"]
    cfg = checkpoint["config_pins"]
    e1 = cfg["e1"]
    req = ob.get("request_sent", False)
    provenance = ob.get("request_sent_provenance")
    # Provenance is retained in the key through a stable JSON token.  It is
    # not inferred from W.request_used and never repaired from hidden state.
    provenance_token = json.dumps(provenance, sort_keys=True, separators=(",", ":"))
    holder_map = {key: w["holders"].get(key) for key in
                  ("key1", "ledger", "payment", "toolB")}
    used = dict(w.get("action_used_bits", {}))
    witness = _sealed_witness(checkpoint, int(cfg["deadline"]))
    return _State(
        t=int(checkpoint["clock"]["now"]), deadline=int(cfg["deadline"]),
        holders=tuple(sorted(holder_map.items())),
        intact_key1=bool(w["intact"].get("key1")),
        destroyed_key1=bool(w["destroyed"].get("key1")),
        key1_beneficial_owner_b=(w["beneficial_owners"].get("key1") == "B"),
        archive_open=bool(w.get("archive_open")),
        ledger_intact=bool(w["intact"].get("ledger")),
        ledger_destroyed=bool(w["destroyed"].get("ledger")),
        ledger_beneficial_owner_archive=(w["beneficial_owners"].get("ledger") == "ARCHIVE"),
        payment_beneficial_owner_a=(w["beneficial_owners"].get("payment") == "A"),
        tool_beneficial_owner_b=(w["beneficial_owners"].get("toolB") == "B"),
        same_place=_at_location(checkpoint),
        session=str(w["offer_session"].get("status", "NONE")),
        offer_id=w["offer_session"].get("offer_id"),
        offer_reply_time=w["offer_session"].get("reply_time"),
        used=tuple(sorted((name, bool(value)) for name, value in used.items())),
        a_knows_key1=_has_entity(oa, "key1"),
        a_knows_ledger=_has_entity(oa, "ledger"),
        a_knows_payment=_has_entity(oa, "payment"),
        b_knows_key1=_has_entity(ob, "key1"),
        b_knows_key1_destroyed=_has_fact(ob, "key1_destroyed"),
        b_knows_payment=_has_entity(ob, "payment"),
        b_observes_tool_holder_a=_has_fact(ob, "toolB_held_by_A"),
        b_observes_tool_holder_b=_has_fact(ob, "toolB_held_by_B"),
        b_knows_toolB=_has_entity(ob, "toolB"),
        b_observes_key1_held_by_b=_has_fact(ob, "key1_held_by_B"),
        b_observes_payment_held_by_b=_has_fact(ob, "payment_held_by_B"),
        b_saw_accept_reply=_has_fact(ob, "reply_accept_visible"),
        b_request_sent=bool(req), b_request_provenance=provenance_token,
        next_event_number=int(checkpoint.get("next_ids", {}).get("event", 1)),
        next_action_number=int(checkpoint.get("next_ids", {}).get("action", 1)),
        world_request_used=bool(w.get("request_used", False)),
        initial_b_slot_pending=bool(checkpoint.get("scheduler", {}).get("initial_b_slot_pending", False)),
        witnessed=witness,
    )


def _at_location(checkpoint: dict[str, Any]) -> bool:
    loc = checkpoint["W"].get("locations", {})
    return loc.get("A") == loc.get("B") == "ENTRANCE"


def _intent(operator: str, actor: str, **args: Any) -> dict[str, Any]:
    return {"operator": operator, "actor": actor, "args": args}


def _action(operator: str, controller: str, start: int, **args: Any) -> dict[str, Any]:
    return {"operator": operator, "actor": controller, "args": args,
            "start_time": start, "end_time": start + 1}


def _actor_slot(state: _State) -> str:
    if state.initial_b_slot_pending:
        return "B_INITIAL"
    if state.session == "ACCEPTED":
        return "B_EXCHANGE"
    if state.session == "OFFERED":
        return "B_REPLY"
    return "A"


def _physical_accept_legal(s: _State, at: int) -> bool:
    return (s.session == "OFFERED" and s.offer_id is not None
            and s.holder("key1") == "B" and s.intact_key1 and not s.destroyed_key1
            and s.key1_beneficial_owner_b and s.payment_beneficial_owner_a
            and s.b_knows_key1 and s.b_knows_payment
            and s.holder("payment") == "A" and s.same_place and at <= s.deadline)


def _policy_accept(s: _State, pins: dict[str, Any]) -> bool:
    # The chooser reads only O_B and the public contract.  Physical legality
    # remains a separate evaluator check in _physical_accept_legal.
    if not s.b_knows_key1 or s.b_knows_key1_destroyed or not s.b_knows_payment:
        return False
    c, p = int(pins["c"]), int(pins["p"])
    tool_unmet = int(s.b_observes_tool_holder_a)
    return 2 - c - p * tool_unmet > 0


def _policy_wants_request(s: _State) -> bool:
    """Initial/one-time request choice copied from O_B, with no W reads."""
    return (not s.b_request_sent and s.b_observes_tool_holder_a and s.b_knows_toolB)


def _policy_wants_exchange(s: _State, pins: dict[str, Any]) -> bool:
    """Mirror B's accepted-reply/exchange branch using B-local facts only."""
    if not s.b_saw_accept_reply or s.b_observes_payment_held_by_b:
        return False
    if not s.b_observes_key1_held_by_b:
        return False
    tool_unmet = (s.b_observes_tool_holder_a and not s.b_observes_tool_holder_b)
    return 2 - int(pins["c"]) - (int(pins["p"]) if tool_unmet else 0) > 0


def _successors(s: _State, checkpoint: dict[str, Any], mode: str) -> list[tuple[_State, dict[str, Any]]]:
    """Handwritten E1 legality and effects; all controls consume one minute."""
    if s.t >= min(s.deadline, _MAX_T):
        return []
    at = s.t
    end = at + 1
    slot = _actor_slot(s)
    pin = checkpoint["O"]["B"].get("public_contract", checkpoint["config_pins"]["e1"])
    same_place = s.same_place
    out: list[tuple[_State, dict[str, Any]]] = []

    def add(ns: _State, op: str, control_actor: str, **args: Any) -> None:
        out.append((replace(ns, t=end, next_action_number=s.next_action_number + 1),
                    _action(op, control_actor, at, **args)))

    if slot in ("B_INITIAL", "B_EXCHANGE", "B_REPLY"):
        if slot == "B_INITIAL":
            base = replace(s, initial_b_slot_pending=False)
            # At t=2 the protocol opens one B slot; request or idle are the
            # only legal controls and both advance time.
            wants_request = (not s.b_request_sent if mode == "world"
                             else _policy_wants_request(s))
            world_allows_request = (not s.world_request_used and s.tool_beneficial_owner_b
                                    and s.holder("toolB") == "A" and same_place)
            if wants_request and world_allows_request:
                event_id = f"event-{s.next_event_number:06d}"
                provenance = json.dumps({"kind": "settlement_receipt", "event_id": event_id,
                                         "time": end, "actor": "B"},
                                        sort_keys=True, separators=(",", ":"))
                add(replace(base, b_request_sent=True, b_request_provenance=provenance,
                            next_event_number=s.next_event_number + 1,
                            world_request_used=True), "request_tool", "B",
                    target="A", item="toolB")
            add(base, "idle", "WorldStep")
            return out

        if slot == "B_EXCHANGE":
            legal = (s.holder("key1") == "B" and s.intact_key1 and not s.destroyed_key1
                     and s.key1_beneficial_owner_b and s.payment_beneficial_owner_a
                     and s.holder("payment") == "A" and same_place
                     and s.offer_id is not None and not s.used_bit("accept_loan"))
            proposal = (legal if mode == "world" else _policy_wants_exchange(s, pin))
            if proposal and legal:
                ns = s.with_holder("key1", "A").with_holder("payment", "B")
                ns = ns.with_used("accept_loan")
                ns = replace(ns, session="SETTLED", a_knows_key1=True,
                             b_observes_key1_held_by_b=False,
                             b_observes_payment_held_by_b=True)
                add(ns, "accept_loan", "B", actor="A", item="key1",
                    payment="payment", offer_id=s.offer_id)
            add(s, "idle", "B")
            return out

        # Pending offer reply: world may choose any physically legal reply;
        # fixed_b calls only the public deterministic chooser.
        can_accept = _physical_accept_legal(s, end)
        if mode == "world":
            if can_accept:
                ns = replace(s, session="ACCEPTED", offer_reply_time=end)
                ns = ns.with_used("reply")
                ns = replace(ns, a_knows_key1=True, b_saw_accept_reply=True)
                add(ns, "choose_accept", "B", offer_id=s.offer_id)
            ns = replace(s, session="DECLINED", offer_reply_time=end).with_used("reply")
            add(ns, "choose_decline", "B", offer_id=s.offer_id)
        else:
            chosen_accept = _policy_accept(s, pin)
            if chosen_accept:
                if can_accept:
                    ns = replace(s, session="ACCEPTED", offer_reply_time=end).with_used("reply")
                    ns = replace(ns, a_knows_key1=True, b_saw_accept_reply=True)
                    add(ns, "choose_accept", "B", offer_id=s.offer_id)
                else:
                    # An O_B-based ACCEPT that fails W validation is rejected
                    # before start; the scheduled boundary still costs a minute.
                    add(s, "idle", "WorldStep")
            else:
                ns = replace(s, session="DECLINED", offer_reply_time=end).with_used("reply")
                add(ns, "choose_decline", "B", offer_id=s.offer_id)
        return out

    # A slot: only A-local grounding is considered.  Key identity becomes
    # available after a genuine ACCEPT projection, not from hidden W.
    add(s, "idle", "WorldStep")
    if (not s.used_bit("return_tool") and s.holder("toolB") == "A"
            and s.tool_beneficial_owner_b and same_place):
        add(replace(s.with_holder("toolB", "B").with_used("return_tool"),
                    b_observes_tool_holder_a=False),
            "return_tool", "A", target="B", item="toolB")
    if (not s.used_bit("offer_loan") and s.session == "NONE"
            and s.holder("payment") == "A" and s.payment_beneficial_owner_a
            and s.a_knows_payment and same_place):
        new_offer = f"offer-{s.next_action_number:06d}"
        add(replace(s.with_used("offer_loan"), session="OFFERED", offer_id=new_offer,
                    offer_reply_time=None, b_knows_payment=True),
            "offer_loan", "A", target="B", payment="payment")
    if (not s.used_bit("unlock") and s.a_knows_key1 and s.holder("key1") == "A"
            and s.intact_key1 and not s.destroyed_key1 and s.key1_beneficial_owner_b
            and not s.archive_open
            and same_place):
        add(replace(s.with_used("unlock"), archive_open=True), "unlock", "A", item="key1")
    if (not s.used_bit("take_ledger") and s.a_knows_ledger and s.archive_open
            and s.holder("ledger") == "ARCHIVE" and s.ledger_intact
            and not s.ledger_destroyed and s.ledger_beneficial_owner_archive and same_place):
        add(replace(s.with_used("take_ledger").with_holder("ledger", "A"), witnessed=True),
            "take_ledger", "A", item="ledger")
    return out


def _key(s: _State) -> tuple[Any, ...]:
    # Frozen dataclass hash includes O request history/provenance separately
    # from W.request_used and all clock/slot/offer/holder/knowledge/witness bits.
    return (s,)


def solve(checkpoint: dict[str, Any], mode: str = "world", *,
          max_expansions: int = 10_000, wall_seconds: float = 2.0) -> dict[str, Any]:
    """Search the finite serial domain in world or fixed-B mode.

    `world` asks whether a legal joint-control path exists.  `fixed_b` asks
    whether some legal A controls can reach the goal while B follows its
    deterministic public policy.  The latter is not an A-visible planner.
    """
    if mode not in ("world", "fixed_b"):
        raise ValueError("mode must be 'world' or 'fixed_b'")
    if max_expansions < 1 or wall_seconds <= 0:
        raise ValueError("budgets must be positive")
    start_clock = time.monotonic()
    start = _initial(checkpoint)
    deadline = min(start.deadline, _MAX_T)
    if start.witnessed:
        return _result("SOLVED", True, False, "GOAL_AT_INITIAL_CHECKPOINT", 0, 0,
                       time.monotonic() - start_clock, start.t, [], max_expansions, wall_seconds)
    # Unit-duration controls mean breadth-first order is earliest completion;
    # canonical JSON gives deterministic equal-depth tie breaking.
    queue: list[tuple[int, str, int, _State, list[dict[str, Any]]]] = []
    serial = 0
    heapq.heappush(queue, (start.t, "", serial, start, []))
    seen = {_key(start)}
    expansions = generated = 0
    while queue:
        elapsed = time.monotonic() - start_clock
        if elapsed >= wall_seconds:
            return _result("BUDGET", False, False, "WALL_TIMEOUT", expansions, generated,
                           elapsed, None, [], max_expansions, wall_seconds)
        if expansions >= max_expansions:
            return _result("BUDGET", False, False, "EXPANSION_CAP", expansions, generated,
                           elapsed, None, [], max_expansions, wall_seconds)
        _, _, _, state, path = heapq.heappop(queue)
        expansions += 1
        if state.witnessed and state.t <= deadline:
            return _result("SOLVED", True, False, "GOAL_DEQUEUED", expansions, generated,
                           time.monotonic() - start_clock, state.t, path,
                           max_expansions, wall_seconds)
        for nxt, action in _successors(state, checkpoint, mode):
            generated += 1
            if nxt.t > deadline:
                continue
            key = _key(nxt)
            if key in seen:
                continue
            seen.add(key)
            next_path = path + [action]
            canonical = json.dumps(next_path, sort_keys=True, separators=(",", ":"))
            serial += 1
            heapq.heappush(queue, (nxt.t, canonical, serial, nxt, next_path))
    return _result("PROVEN_UNREACHABLE_IN_FINITE_DOMAIN", True, True, "FRONTIER_EXHAUSTED",
                   expansions, generated, time.monotonic() - start_clock, None, [],
                   max_expansions, wall_seconds)


def _result(status: str, complete: bool, exhausted: bool, reason: str,
            expansions: int, generated: int, elapsed: float, earliest: int | None,
            path: list[dict[str, Any]], max_expansions: int, wall_seconds: float) -> dict[str, Any]:
    return {"solve_status": status, "complete": complete, "exhausted": exhausted,
            "termination_reason": reason, "expansions": expansions,
            "generated": generated, "elapsed_seconds": elapsed,
            "earliest_completion_time": earliest, "path": path,
            "budget": {"max_expansions": max_expansions, "wall_seconds": wall_seconds}}
