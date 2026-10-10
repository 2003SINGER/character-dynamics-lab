"""Player-visible management commands for the bounded native P3 scene."""

from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB

from .agency import get_value, set_value
from .scene import create_scene


def _scene_actor(caller):
    actor_id = caller.attributes.get("native_p3_courier_id", category="native_p3")
    if not actor_id:
        return None
    return ObjectDB.objects.filter(id=actor_id).first()


def _owned(caller, actor):
    return bool(actor and caller.account and get_value(actor, "owner_account_id") == caller.account.id)


class CmdP3Start(Command):
    key = "p3-start"
    locks = "cmd:all()"
    help_category = "P3 Autonomous Scene"
    help = "Create a fresh isolated courier/resident scene and start its persistent timer."

    def func(self):
        parts = (self.args or "").split()
        mode = parts[0].lower() if parts else "a"
        try:
            interval = int(parts[1]) if len(parts) > 1 else 4
            seed = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            self.caller.msg("Usage: p3-start [a|b] [interval_seconds: 2..30] [seed: nonnegative integer].")
            return
        if len(parts) > 3 or not 2 <= interval <= 30 or seed < 0:
            self.caller.msg("Usage: p3-start [a|b] [interval_seconds: 2..30] [seed: nonnegative integer].")
            return
        if mode not in ("a", "b"):
            self.caller.msg("Usage: p3-start [a|b] [interval_seconds: 2..30] [seed: nonnegative integer] (default: a 4 0).")
            return
        scene = create_scene(self.caller, mode=mode, interval=interval, seed=seed)
        self.caller.attributes.add("native_p3_courier_id", scene["courier"].id, category="native_p3")
        self.caller.attributes.add("native_p3_actor_ids", [actor.id for actor in scene["actors"]],
                                   category="native_p3")
        self.caller.attributes.add("native_p3_scene_id", scene["scene_id"], category="native_p3")
        actors = ", ".join(actor.dbref for actor in scene["actors"])
        detail = (f" independent actors {actors} have separate existing parcels "
                  f"{scene['supply'].dbref} and {scene['return_parcel'].dbref} to deliver") if mode == "b" else (
                  f" one courier {scene['courier'].dbref} will collect existing supply {scene['supply'].dbref}")
        self.caller.msg(f"P3-{mode.upper()} scene {scene['scene_id']} started;{detail}; "
                        f"destination {scene['destination'].dbref}; timer interval {interval}s.")


class CmdP3Status(Command):
    key = "p3-status"
    locks = "cmd:all()"
    help_category = "P3 Autonomous Scene"
    help = "Show the latest persisted scene state and pending action."

    def func(self):
        actor = _scene_actor(self.caller)
        if not _owned(self.caller, actor):
            self.caller.msg("No P3 scene is assigned to this account. Use p3-start.")
            return
        rows = []
        for actor_id in self.caller.attributes.get("native_p3_actor_ids", category="native_p3", default=[]):
            member = ObjectDB.objects.filter(id=actor_id).first()
            if not _owned(self.caller, member):
                continue
            pending = get_value(member, "pending_action")
            pending_social = get_value(member, "pending_social")
            last = get_value(member, "last_outcome")
            obs = get_value(member, "last_observation", {})
            rows.append(
                f"{member.key} {member.dbref} status={get_value(member, 'status')} "
                f"ticks={get_value(member, 'tick_count', 0)} room={member.location.dbref if member.location else 'none'} "
                f"item={get_value(member, 'task_item_dbref')} "
                f"destination={get_value(member, 'task_destination_dbref')} "
                f"interval={get_value(member, 'interval_seconds', 4)}s seed={get_value(member, 'scenario_seed', 0)} "
                f"observed_room={obs.get('observation', {}).get('room_id')} "
                f"pending={pending} pending_social={pending_social} last_outcome={last}"
            )
        self.caller.msg("\n".join(rows) if rows else "No P3 actors are available.")


class CmdP3Stop(Command):
    key = "p3-stop"
    locks = "cmd:all()"
    help_category = "P3 Autonomous Scene"
    help = "Pause this scene's persistent timer while preserving actor state and logs."

    def func(self):
        actor = _scene_actor(self.caller)
        if not _owned(self.caller, actor):
            self.caller.msg("No P3 scene is assigned to this account.")
            return
        stopped = 0
        for actor_id in self.caller.attributes.get("native_p3_actor_ids", category="native_p3", default=[]):
            member = ObjectDB.objects.filter(id=actor_id).first()
            if not _owned(self.caller, member):
                continue
            script_id = get_value(member, "script_id")
            script = ScriptDB.objects.filter(id=script_id).first()
            if script:
                script.stop()
            set_value(member, "status", "PAUSED")
            stopped += 1
        self.caller.msg(f"P3 {get_value(actor, 'scene_id')} paused {stopped} actor timers; state and logs are preserved.")


class CmdP3Log(Command):
    key = "p3-log"
    locks = "cmd:all()"
    help_category = "P3 Autonomous Scene"
    help = "Show the most recent persisted actor observations, proposals, and settlements."

    def func(self):
        actor = _scene_actor(self.caller)
        if not _owned(self.caller, actor):
            self.caller.msg("No P3 scene is assigned to this account.")
            return
        events = []
        for actor_id in self.caller.attributes.get("native_p3_actor_ids", category="native_p3", default=[]):
            member = ObjectDB.objects.filter(id=actor_id).first()
            if _owned(self.caller, member):
                events.extend((member.key, row) for row in get_value(member, "log", [])[-10:])
        self.caller.msg("P3 event log (latest first):\n" +
                        "\n".join(f"{actor_key}: {row!r}" for actor_key, row in reversed(events[-20:])))


class P3CmdSet(CmdSet):
    key = "P3 commands"

    def at_cmdset_creation(self):
        self.add(CmdP3Start())
        self.add(CmdP3Status())
        self.add(CmdP3Stop())
        self.add(CmdP3Log())


def install_commands(caller):
    """Install commands on the invoking account/character from Evennia's py command."""
    caller.cmdset.add(P3CmdSet, persistent=True)
    return "P3 commands installed."
