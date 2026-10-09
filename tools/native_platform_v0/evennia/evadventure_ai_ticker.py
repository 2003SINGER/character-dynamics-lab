"""Minimal scheduler adapter for the official EvAdventure AIHandler.

This does not define NPC states or action logic. It periodically invokes the
official EvAdventureMob.ai.run() state machine and records movement evidence.
"""

import random
from datetime import datetime, timezone

from evennia import DefaultScript
from evennia.objects.models import ObjectDB
from evennia.contrib.tutorials.evadventure import npcs as evadventure_npcs
from evennia.contrib.tutorials.evadventure.npcs import EvAdventureMob

# Official Evennia 6.0.0 npcs.py calls random.choice in ai_roam/ai_flee but
# imports only `choice`; provide its missing module name without editing the
# installed wheel or replacing the upstream state/action methods.
evadventure_npcs.random = random


class EvAdventureAITicker(DefaultScript):
    """Tick official EvAdventure mobs every five seconds."""

    def at_script_creation(self):
        self.key = "native-p1-evadventure-ai-ticker"
        self.desc = "Calls the stock EvAdventure AIHandler on live mobs."
        self.interval = 5
        self.persistent = True

    def at_repeat(self):
        for npc in ObjectDB.objects.all():
            if not npc.is_typeclass(EvAdventureMob, exact=False):
                continue
            if not npc.location:
                continue

            before = npc.location.id
            state_before = npc.ai.get_state()
            npc.ai.run()
            after = npc.location.id if npc.location else None
            count = npc.attributes.get("native_p1_tick_count", category="native_p1", default=0)
            npc.attributes.add("native_p1_tick_count", count + 1, category="native_p1")
            npc.attributes.add("native_p1_last_tick_state", state_before, category="native_p1")
            npc.attributes.add("native_p1_last_tick_from", before, category="native_p1")
            npc.attributes.add("native_p1_last_tick_to", after, category="native_p1")
            events = npc.attributes.get("native_p1_tick_events", category="native_p1", default=[])
            events.append(
                (datetime.now(timezone.utc).isoformat(), count + 1, state_before, before, after)
            )
            npc.attributes.add("native_p1_tick_events", events[-40:], category="native_p1")
