"""Command-backed physical operations for the opt-in ongoing-station content."""
from __future__ import annotations

from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet


class CmdStationStore(Command):
    key = "station-store"
    locks = "cmd:all()"
    help_category = "P5 Ongoing Station"
    help = "Store an inspected station supply in its registered storage container."

    def func(self):
        actor = self.caller
        if not actor.attributes.get("p5_station_profile_enabled", category="native_p5", default=False):
            actor.msg("This station operation is not available here.")
            return
        try:
            item_id = int((self.args or "").strip())
        except (TypeError, ValueError):
            actor.msg("Usage: station-store <exact item id>")
            return
        from tools.native_platform_v0.p5 import service
        from tools.native_platform_v0.p5.ongoing_station.work import store_supply
        result = store_supply(actor, item_id=item_id)
        actor.attributes.add("p5_station_last_store_result", result, category="native_p5")
        actor.msg("Station storage settled." if result.get("settled") else
                  f"Station storage rejected: {result.get('reason', 'native validation failed')}.")


class CmdStationRequestLoan(Command):
    key = "station-request-loan"
    locks = "cmd:all()"
    help_category = "P5 Ongoing Station"
    help = "Ask co-present registered A to lend the registered station tool to B by a minute."

    def func(self):
        player = self.caller
        parts = (self.args or "").split()
        if len(parts) != 4:
            player.msg("Usage: station-request-loan <tool-id> A B <absolute-due-minute>")
            return
        try:
            tool_id, due_minute = int(parts[0]), int(parts[3])
        except ValueError:
            player.msg("Tool id and due minute must be integers.")
            return
        from tools.native_platform_v0.p5.ongoing_station.work import request_tool_loan
        result = request_tool_loan(player, tool_id=tool_id, lender_alias=parts[1],
                                   borrower_alias=parts[2], due_minute=due_minute)
        player.msg("Station-tool request recorded." if result.get("settled") else
                   f"Station-tool request rejected: {result.get('reason', 'native validation failed')}.")


class StationContentCmdSet(CmdSet):
    key = "P5 ongoing station content"

    def at_cmdset_creation(self):
        self.add(CmdStationStore())
        self.add(CmdStationRequestLoan())


def install(actor):
    actor.cmdset.add(StationContentCmdSet, persistent=False)
