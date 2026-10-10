"""Fresh, non-overwriting native Evennia courier scene construction."""

from datetime import datetime, timezone
import secrets

from evennia import create_object, create_script


def create_scene(owner, mode="a", interval=4, drive="timer", seed=0, drive_mode=None):
    from typeclasses.characters import Character
    from typeclasses.exits import Exit
    from typeclasses.objects import Object
    from typeclasses.rooms import Room

    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3)
    if mode not in ("a", "b"):
        raise ValueError("P3 scene mode must be 'a' or 'b'")
    if type(interval) is not int or not 2 <= interval <= 30:
        raise ValueError("P3 timer interval must be an integer in [2,30] seconds")
    drive = drive_mode if drive_mode is not None else drive
    if drive not in ("timer", "manual"):
        raise ValueError("P3 drive must be 'timer' or 'manual'")
    if type(seed) is not int or seed < 0:
        raise ValueError("P3 scenario seed must be a nonnegative integer")
    pickup = create_object(Room, key=f"Courier Pickup {suffix}",
                           attributes=[("p3_scene_id", suffix, "native_p3")])
    destination = create_object(Room, key=f"Resident Porch {suffix}",
                                 attributes=[("p3_scene_id", suffix, "native_p3")])
    create_object(Exit, key="east", location=pickup, destination=destination,
                  attributes=[("p3_scene_id", suffix, "native_p3")])
    create_object(Exit, key="west", location=destination, destination=pickup,
                  attributes=[("p3_scene_id", suffix, "native_p3")])
    courier = create_object(Character, key=f"Courier {suffix}", location=pickup,
                            attributes=[("p3_scene_id", suffix, "native_p3"),
                                         ("owner_account_id", owner.account.id, "native_p3"),
                                         ("p3_goal", "deliver_supply", "native_p3")])
    actors = [courier]
    if mode == "b":
        resident = create_object(Character, key=f"Resident {suffix}", location=pickup,
                                 attributes=[("p3_scene_id", suffix, "native_p3"),
                                             ("owner_account_id", owner.account.id, "native_p3"),
                                             ("p3_goal", "deliver_supply", "native_p3"),
                                             ("ensemble_character_id", "love", "ensemble_bridge")])
        courier.attributes.add("ensemble_character_id", "hero", category="ensemble_bridge")
        courier.attributes.add("p3_social_target_id", resident.id, category="native_p3")
        resident.attributes.add("p3_social_target_id", courier.id, category="native_p3")
        actors.append(resident)
    else:
        resident = create_object(Object, key=f"Resident Porch Marker {suffix}", location=destination,
                                 attributes=[("p3_scene_id", suffix, "native_p3"),
                                              ("p3_role", "delivery_destination_marker", "native_p3")])
    supply = create_object(Object, key=f"Supply {suffix}", location=pickup,
                           attributes=[("p3_scene_id", suffix, "native_p3"),
                                        ("p3_role", "assigned_supply", "native_p3")])
    return_parcel = None
    if mode == "b":
        return_parcel = create_object(Object, key=f"Resident Parcel {suffix}", location=pickup,
                                      attributes=[("p3_scene_id", suffix, "native_p3"),
                                                   ("p3_role", "resident_assigned_parcel", "native_p3")])
    courier.attributes.add("task_item_id", supply.id, category="native_p3")
    courier.attributes.add("task_item_key", supply.key, category="native_p3")
    courier.attributes.add("task_destination_id", destination.id, category="native_p3")
    courier.attributes.add("task_destination_dbref", destination.dbref, category="native_p3")
    courier.attributes.add("task_item_dbref", supply.dbref, category="native_p3")
    courier.attributes.add("resident_id", resident.id, category="native_p3")
    courier.attributes.add("scene_id", suffix, category="native_p3")
    courier.attributes.add("mode", mode, category="native_p3")
    courier.attributes.add("interval_seconds", interval, category="native_p3")
    courier.attributes.add("drive_mode", drive, category="native_p3")
    courier.attributes.add("scenario_seed", seed, category="native_p3")
    courier.attributes.add("status", "RUNNING", category="native_p3")
    courier.attributes.add("tick_count", 0, category="native_p3")
    courier.attributes.add("log", [], category="native_p3")
    if mode == "b":
        resident.attributes.add("task_item_id", return_parcel.id, category="native_p3")
        resident.attributes.add("task_item_key", return_parcel.key, category="native_p3")
        resident.attributes.add("task_item_dbref", return_parcel.dbref, category="native_p3")
        resident.attributes.add("task_destination_id", destination.id, category="native_p3")
        resident.attributes.add("task_destination_dbref", destination.dbref, category="native_p3")
        resident.attributes.add("resident_id", courier.id, category="native_p3")
        resident.attributes.add("scene_id", suffix, category="native_p3")
        resident.attributes.add("mode", mode, category="native_p3")
        resident.attributes.add("interval_seconds", interval, category="native_p3")
        resident.attributes.add("drive_mode", drive, category="native_p3")
        resident.attributes.add("scenario_seed", seed, category="native_p3")
        resident.attributes.add("status", "RUNNING", category="native_p3")
        resident.attributes.add("tick_count", 0, category="native_p3")
        resident.attributes.add("log", [], category="native_p3")
    scripts = []
    for actor in actors:
        script = create_script("tools.native_platform_v0.p3.agency.P3AutonomyScript", obj=actor,
                               key=f"native-p3-autonomy-{actor.id}-{suffix}",
                               # Evennia's db_interval is a non-null integer. Zero keeps
                               # manual fixtures persistent but unscheduled.
                               interval=interval if drive == "timer" else 0,
                               persistent=True, autostart=(drive == "timer"))
        actor.attributes.add("script_id", script.id, category="native_p3")
        scripts.append(script)
    return {"mode": mode, "scene_id": suffix, "courier": courier, "resident": resident,
            "actors": actors, "supply": supply, "return_parcel": return_parcel,
            "pickup": pickup, "destination": destination, "scripts": scripts}
