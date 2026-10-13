"""Evennia persistence and future-only author attachment transitions."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from collections.abc import Mapping, Sequence

from .model import AUTHOR_SCHEMA, PROFILE_SCHEMA, compile_projection, load_profile, validate_author


def _plain(value):
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(v) for v in value]
    return value


def _digest(value):
    return sha256(json.dumps(_plain(value), sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def initialize_station(pickup, actors, raw_profile):
    """Enable the autonomous profile; an attached author bundle remains inactive."""
    profile = load_profile(_plain(raw_profile))
    if profile is None:
        return None
    pickup.attributes.add("p5_ongoing_station_profile", _plain(profile.raw), category="native_p5")
    if profile.author is not None:
        pickup.attributes.add("p5_ongoing_station_staged_author", _plain(profile.author), category="native_p5")
    pickup.attributes.add("p5_ongoing_station_meta", {
        "status": "ACTIVE", "station_id": profile.station_id,
        "profile_version": profile.version, "horizon": profile.horizon,
        "source_sha256": _digest(profile.raw), "author_status": "STAGED_INACTIVE" if profile.author else "ABSENT",
        "active_author_version": None, "projection_history": [], "activation_event_ids": [],
        "stale_projection_ids": [],
    }, category="native_p5")
    for actor in actors.values():
        actor.attributes.add("ongoing_commitments", [], category="native_p5")
        actor.attributes.add("ongoing_task_offer", None, category="native_p5")
        actor.attributes.add("ongoing_goal_history", [], category="native_p5")
    return profile


def profile_for(pickup):
    raw = pickup.attributes.get("p5_ongoing_station_profile", category="native_p5")
    return load_profile(_plain(raw)) if raw is not None else None


def meta_for(pickup):
    return _plain(pickup.attributes.get("p5_ongoing_station_meta", category="native_p5", default={}))


def _store_meta(pickup, meta):
    pickup.attributes.add("p5_ongoing_station_meta", _plain(meta), category="native_p5")


def activate_author(pickup, *, expected_version, now, entities=None):
    """Activate an author attachment after the world is running; never edits W."""
    profile = profile_for(pickup)
    if profile is None or profile.author is None:
        return {"ok": False, "status": "NO_STAGED_AUTHOR"}
    meta = meta_for(pickup)
    current = pickup.attributes.get("p5_ongoing_station_staged_author", category="native_p5")
    if current is None:
        current = profile.author
    current = validate_author(_plain(current))
    current_bundle_version = int(current["bundle"]["version"])
    if type(expected_version) is not int or expected_version != current_bundle_version:
        return {"ok": False, "status": "VERSION_CONFLICT", "active_version": current_bundle_version}
    proposed = current
    projection = compile_projection(
        load_profile({**_plain(profile.raw), "author": _plain(proposed)}), entities=entities)
    if proposed["bundle"]["bundle_id"] != current["bundle"]["bundle_id"]:
        return {"ok": False, "status": "IDENTITY_IMMUTABLE"}
    if int(proposed["bundle"]["version"]) != current_bundle_version:
        return {"ok": False, "status": "VERSION_CONFLICT", "active_version": current_bundle_version}
    if meta.get("author_status") == "ACTIVE":
        return {"ok": False, "status": "ALREADY_ACTIVE"}
    meta["author_status"] = "ACTIVE"
    meta["active_author_version"] = current_bundle_version
    meta["projection_history"] = list(meta.get("projection_history", [])) + [
        {"projection_id": f"{profile.station_id}:{current_bundle_version}:{projection.source_sha256[:12]}",
         "bundle_id": projection.bundle_id, "version": projection.version,
         "source_sha256": projection.source_sha256, "activated_minute": int(now),
         "constraint_ids": [row["constraint_id"] for row in projection.constraints]}]
    _store_meta(pickup, meta)
    pickup.attributes.add("p5_ongoing_station_author", _plain(proposed), category="native_p5")
    return {"ok": True, "status": "ACTIVATED", "station_id": profile.station_id,
            "version": current_bundle_version, "source_sha256": projection.source_sha256,
            "constraint_ids": [row["constraint_id"] for row in projection.constraints],
            "activated_minute": int(now)}


def edit_author(pickup, raw_author, *, expected_version, now, completed_ids=(), evidenced_ids=(), entities=None):
    """CAS a future author source version while preserving settled requirements and control grant."""
    profile = profile_for(pickup)
    meta = meta_for(pickup)
    current = pickup.attributes.get("p5_ongoing_station_author", category="native_p5")
    if profile is None or current is None or meta.get("author_status") != "ACTIVE":
        return {"ok": False, "status": "AUTHOR_NOT_ACTIVE"}
    current = validate_author(_plain(current))
    proposed = validate_author(raw_author)
    old_bundle, new_bundle = current["bundle"], proposed["bundle"]
    version = int(old_bundle["version"])
    if type(expected_version) is not int or expected_version != version:
        return {"ok": False, "status": "VERSION_CONFLICT", "active_version": version}
    if (new_bundle["bundle_id"] != old_bundle["bundle_id"] or
            type(new_bundle["version"]) is not int or new_bundle["version"] != version + 1):
        return {"ok": False, "status": "IDENTITY_OR_VERSION_INVALID", "active_version": version}
    old_bindings = {r["constraint_id"]: r for r in current["bindings"]}
    new_bindings = {r["constraint_id"]: r for r in proposed["bindings"]}
    for cid, old in old_bindings.items():
        new = new_bindings.get(cid)
        if new is None:
            return {"ok": False, "status": "BINDING_REMOVED", "constraint_id": cid}
        if old["control"]["mode"] != new["control"]["mode"] or old["control"]["source"] != new["control"]["source"]:
            return {"ok": False, "status": "CONTROL_MODE_IMMUTABLE", "constraint_id": cid}
        if old["locked_fragment"] != new["locked_fragment"]:
            return {"ok": False, "status": "LOCKED_CORE_IMMUTABLE", "constraint_id": cid}
        if cid in set(completed_ids) | set(evidenced_ids) and old != new:
            return {"ok": False, "status": "SETTLED_BINDING_IMMUTABLE", "constraint_id": cid}
        if any(old["control"][key] != new["control"][key]
               for key in ("file_actor", "allowed_methods")):
            continue
    from tools.native_platform_v0.p5.bundle import BundleStore, load_bundle
    from tools.native_platform_v0.p5.story_process.model import story_event_registry
    active_bundle = load_bundle(old_bundle, registry=story_event_registry(), entities=entities)
    store = BundleStore(active_bundle, registry=story_event_registry(), entities=entities)
    try:
        store.replace(new_bundle, expected_version, now=now,
                      completed_constraint_ids=set(completed_ids),
                      evidence_constraint_ids=set(evidenced_ids))
    except Exception as exc:
        return {"ok": False, "status": getattr(exc, "code", "INVALID_EDIT"), "reason": str(exc)}
    new_projection = compile_projection(
        load_profile({**_plain(profile.raw), "author": _plain(proposed)}), entities=entities)
    stale = [row.get("projection_id") for row in meta.get("projection_history", [])
             if row.get("version") == version]
    meta["active_author_version"] = version + 1
    meta["stale_projection_ids"] = list(meta.get("stale_projection_ids", [])) + stale
    meta["projection_history"] = list(meta.get("projection_history", [])) + [
        {"projection_id": f"{profile.station_id}:{version + 1}:{new_projection.source_sha256[:12]}",
         "bundle_id": new_projection.bundle_id, "version": new_projection.version,
         "source_sha256": new_projection.source_sha256, "activated_minute": int(now),
         "constraint_ids": [row["constraint_id"] for row in new_projection.constraints]}]
    pickup.attributes.add("p5_ongoing_station_author", _plain(proposed), category="native_p5")
    _store_meta(pickup, meta)
    return {"ok": True, "status": "UPDATED", "previous_version": version,
            "version": version + 1, "source_sha256": new_projection.source_sha256,
            "stale_projection_ids": stale,
            "constraint_ids": [row["constraint_id"] for row in new_projection.constraints]}


def active_projection(pickup, *, entities=None):
    profile = profile_for(pickup)
    meta = meta_for(pickup)
    if profile is None or meta.get("author_status") != "ACTIVE":
        return None
    raw = pickup.attributes.get("p5_ongoing_station_author", category="native_p5")
    if raw is None:
        return None
    return compile_projection(load_profile({**_plain(profile.raw), "author": _plain(raw)}),
                              entities=entities)


__all__ = ["initialize_station", "profile_for", "meta_for", "activate_author", "edit_author",
           "active_projection"]
