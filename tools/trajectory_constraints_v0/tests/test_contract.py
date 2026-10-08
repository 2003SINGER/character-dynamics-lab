import json
from pathlib import Path
import unittest
from fractions import Fraction as F

from trajectory_constraints_v0.ast import (
    Anchor, AnchorKind, And, Compare, CompareValue, EnumTransitionSequence, EventCount,
    EventOrder, Not, NumericBand, NumericLiteral, Or, Occurrence, TemporalConstraint,
    TemporalOp, TimeWeightedMeanDifference, Trigger, Window, StrictOrder,
    SequenceMode, ast_from_json, ast_to_json,
)
from trajectory_constraints_v0.compiler import (
    Compatibility, compile_constraint, detect_hard_conflict, verify_migration,
)
from trajectory_constraints_v0.editor import (
    EnvelopeInterpretation, EventNode, compile_envelope, compile_event_dag,
    compile_event_milestone, compile_state_point,
)
from trajectory_constraints_v0.monitor import MonitorSession, Verdict, evaluate
from trajectory_constraints_v0.monitor import _tri
from trajectory_constraints_v0.projectors import actor_belief, factive_observer_knows, task_progress, world_holding
from trajectory_constraints_v0.trace import Event, Point, Segment, Trace
from trajectory_constraints_v0.types import (
    MissingPolicy, Owner, Registry, RegistryEntry, StableEntity, TimeMode,
    TypeSpec, ValueKind, ValueRef, exact_time,
)
from trajectory_constraints_v0.evaluation import project_registered


def make_registry():
    return Registry((
        RegistryEntry("world.progress", "1", Owner.WORLD, "WorldTask", {"task":"WorldTask"},
            TypeSpec(ValueKind.REAL,"fraction",lower=0,upper=1),"task_progress_fraction_v1",
            ("WorldTask.effort_done","WorldTask.effort_target"),TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("world.holding", "1", Owner.WORLD, "Holding", {"actor":"Actor","item":"Item"},
            TypeSpec(ValueKind.BOOL),"world_holding_v1",("World.holds",),TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("actor.belief", "1", Owner.ACTOR_O, "Belief", {"actor":"Actor","proposition":"str"},
            TypeSpec(ValueKind.BOOL),"actor_belief_v1",("ObservationFact",),TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("observer.knows", "1", Owner.WORLD, "Knowledge", {"observer":"Actor","proposition":"str"},
            TypeSpec(ValueKind.BOOL),"factive_observer_knows_v1",("ObservationFact","World.truth","Evidence.provenance"),TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("actor.anxiety", "model-A", Owner.ACTOR_S, "ActorState", {"actor":"Actor"},
            TypeSpec(ValueKind.REAL,"control_unit",lower=0,upper=1),"registered_field_v1",("ActorState.anxiety",),TimeMode.CERTIFIED_POLYNOMIAL,model_pin="dyn-A@4"),
        RegistryEntry("world.quest_phase", "1", Owner.WORLD, "Quest", {"quest":"Quest"},
            TypeSpec(ValueKind.ENUM,enum_values=("PLANNED","ACTIVE","COMPLETE")),"registered_field_v1",("Quest.phase",),TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("belief_revision", "1", Owner.LEDGER, "BeliefRevision", {"actor":"str"},TypeSpec(ValueKind.EVENT),"ledger_event_v1",("Ledger.belief_revision",),TimeMode.EVENT),
        RegistryEntry("secret", "1", Owner.LEDGER, "SecretEvent", {},TypeSpec(ValueKind.EVENT),"ledger_event_v1",("Ledger.secret",),TimeMode.EVENT),
        RegistryEntry("clue", "1", Owner.LEDGER, "ClueEvent", {},TypeSpec(ValueKind.EVENT),"ledger_event_v1",("Ledger.clue",),TimeMode.EVENT),
        RegistryEntry("reveal", "1", Owner.LEDGER, "RevealEvent", {},TypeSpec(ValueKind.EVENT),"ledger_event_v1",("Ledger.reveal",),TimeMode.EVENT),
        RegistryEntry("item_destroyed", "1", Owner.LEDGER, "ItemDestroyed", {"item":"Item"},TypeSpec(ValueKind.EVENT),"ledger_event_v1",("Ledger.item_destroyed",),TimeMode.EVENT),
    ))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.registry=make_registry()
        self.actor=StableEntity("Actor","actor-1","A")
        self.item=StableEntity("Item","ledger-1","Ledger")
        self.quest=StableEntity("Quest","quest-1","Q")
        self.holding=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item},Owner.WORLD)
        self.anxiety=ValueRef("actor.anxiety","model-A",{"actor":self.actor},Owner.ACTOR_S)

    def trace(self, now=0): return Trace(now=now)

    def test_exact_simulation_time(self):
        self.assertEqual(exact_time("1.25"),F(5,4))
        for bad in (True,1.0,float("nan"),float("inf")):
            with self.assertRaises((TypeError,ValueError)): exact_time(bad)

    def test_registry_pins_allowlist_ranges_and_json_roundtrip(self):
        with self.assertRaises(ValueError): self.registry.add(self.registry.entries()[0])
        with self.assertRaises(ValueError): Registry((RegistryEntry("x","1",Owner.WORLD,"T",{},TypeSpec(ValueKind.BOOL),"arbitrary_python",(),TimeMode.POINT_ONLY),))
        encoded=json.dumps(self.registry.to_json(),sort_keys=True)
        self.assertEqual(Registry.from_json(json.loads(encoded)).to_json(),self.registry.to_json())
        payload=ast_to_json(NumericBand("x",self.holding,Window("0","10",True,False),0,1))
        restored=ast_from_json(json.loads(json.dumps(payload)))
        self.assertEqual(restored,NumericBand("x",self.holding,Window(0,10,True,False),0,1))

    def test_admission_rejections_unknown_owner_types_units_enum_pin_time_interpolation(self):
        # trust is deliberately not registered.
        with self.assertRaises(KeyError): compile_constraint(TemporalConstraint("trust",TemporalOp.AT,
            CompareValue(ValueRef("trust","1",{}),Compare.EQ,True),Window(0,0)),self.registry)
        wrong=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item},Owner.ACTOR_O)
        with self.assertRaises(TypeError): compile_constraint(TemporalConstraint("owner",TemporalOp.AT,CompareValue(wrong,Compare.EQ,True),Window(0,0)),self.registry)
        with self.assertRaises(TypeError): compile_constraint(TemporalConstraint("unit",TemporalOp.AT,CompareValue(self.anxiety,Compare.LE,NumericLiteral(F(1,2),"kg")),Window(0,0)),self.registry)
        with self.assertRaises(ValueError): compile_constraint(EnumTransitionSequence("enum",ValueRef("world.quest_phase","1",{"quest":self.quest}),("UNKNOWN","COMPLETE"),SequenceMode.EXACT,Window(0,1)),self.registry)
        with self.assertRaises(KeyError): compile_constraint(TemporalConstraint("pin",TemporalOp.AT,CompareValue(ValueRef("actor.anxiety","missing",{"actor":self.actor}),Compare.GE,NumericLiteral(0,"control_unit")),Window(0,0)),self.registry)
        with self.assertRaises(TypeError): exact_time(3.14)
        with self.assertRaises(ValueError): compile_envelope("no_interp",self.anxiety,((F(0),F(0),F(1)),),unit="control_unit",interpretation=None)
        with self.assertRaises(ValueError): compile_envelope("single-linear",self.anxiety,((F(0),F(0),F(1)),),unit="control_unit",interpretation=EnvelopeInterpretation.LINEAR)
        with self.assertRaises(ValueError): compile_envelope("single-hold",self.anxiety,((F(0),F(0),F(1)),),unit="control_unit",interpretation=EnvelopeInterpretation.HOLD)
        with self.assertRaises(ValueError): TemporalConstraint("bad-at",TemporalOp.AT,CompareValue(self.holding,Compare.EQ,True),Window(0,5))
        with self.assertRaises(ValueError): Window(3,3,True,False)
        with self.assertRaises(TypeError): compile_constraint(NumericBand("wrong-unit",self.anxiety,Window(0,1),0,1,unit="kg"),self.registry)
        with self.assertRaises(TypeError): compile_constraint(NumericBand("missing-unit",self.anxiety,Window(0,1),0,1),self.registry)

    def test_projectors_are_pure_and_fact_bound(self):
        self.assertEqual(task_progress({"effort_done":"3","effort_target":"4"}).value,F(3,4))
        self.assertFalse(task_progress({"effort_done":"5","effort_target":"4"}).known)
        self.assertFalse(task_progress({"effort_done":"0","effort_target":"0"}).known)
        self.assertEqual(world_holding({"world_holds":{("actor-1","ledger-1")}},"actor-1","ledger-1").value,True)
        snap={"actor_beliefs":{"actor-1":{"p":True}},"world_truth":{"p":False},"legal_evidence":{"actor-1":{"p"}}}
        self.assertEqual(actor_belief(snap,"actor-1","p").value,True)
        self.assertEqual(factive_observer_knows(snap,"actor-1","p").value,False)
        self.assertFalse(factive_observer_knows({},"actor-1","p").known)
        missing_provenance={"actor_beliefs":{"actor-1":{"p":True}},"world_truth":{"p":True}}
        self.assertFalse(factive_observer_knows(missing_provenance,"actor-1","p").known)
        snap["world_truth"]["p"]=True
        self.assertEqual(factive_observer_knows(snap,"actor-1","p").value,True)
        snap["legal_evidence"]["actor-1"].clear()
        self.assertEqual(factive_observer_knows(snap,"actor-1","p").value,False)

    def test_stable_deleted_identity_is_indeterminate_unless_exists_false_registered(self):
        t=self.trace(1); t.add_point(Point(self.holding,0,True)); t.delete_entity("ledger-1",1)
        c=TemporalConstraint("gone",TemporalOp.AT,CompareValue(self.holding,Compare.EQ,True),Window(0,0))
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.SATISFIED)
        cnow=TemporalConstraint("at-delete",TemporalOp.AT,CompareValue(self.holding,Compare.EQ,True),Window(0,0),Anchor(AnchorKind.FIXED_ABSOLUTE,absolute_time=1))
        self.assertEqual(evaluate(cnow,t,self.registry)[0].verdict,Verdict.INDETERMINATE)
        false_registry=Registry(self.registry.entries()+(RegistryEntry("world.exists","1",Owner.WORLD,"Item",{"item":"Item"},TypeSpec(ValueKind.BOOL),"registered_field_v1",("World.items",),TimeMode.PIECEWISE_CONSTANT,MissingPolicy.EXISTS_FALSE),))
        ref=ValueRef("world.exists","1",{"item":self.item})
        c2=TemporalConstraint("gone-false",TemporalOp.AT,CompareValue(ref,Compare.EQ,False),Window(0,0),Anchor(AnchorKind.FIXED_ABSOLUTE,absolute_time=1))
        self.assertEqual(evaluate(c2,t,false_registry)[0].verdict,Verdict.SATISFIED)

    def test_eventually_pending_then_inclusive_deadline_witness_and_open_endpoint(self):
        r=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item})
        c=TemporalConstraint("get-it",TemporalOp.EVENTUALLY,CompareValue(r,Compare.EQ,True),Window(0,10,True,True))
        t=self.trace(5); t.add_point(Point(r,0,False)); t.add_point(Point(r,5,False))
        t.seal_values_through(r,5)
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.PENDING)
        t.advance(10); t.add_point(Point(r,10,True))
        t.seal_values_through(r,10)
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.SATISFIED)
        open_c=TemporalConstraint("open",TemporalOp.EVENTUALLY,CompareValue(r,Compare.EQ,True),Window(0,10,True,False))
        t2=self.trace(10); t2.add_point(Point(r,0,False)); t2.add_point(Point(r,10,True))
        t2.seal_values_through(r,10)
        self.assertEqual(evaluate(open_c,t2,self.registry)[0].verdict,Verdict.VIOLATED)

    def test_piecewise_hold_and_conclusions_require_completeness_seals(self):
        r=self.holding
        t=self.trace(10); t.add_point(Point(r,0,True)); t.add_point(Point(r,10,True))
        c=TemporalConstraint("holds",TemporalOp.ALWAYS,CompareValue(r,Compare.EQ,True),Window(0,10))
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.INDETERMINATE)
        self.assertIsNone(_tri(CompareValue(r,Compare.EQ,True),5,t,self.registry))
        t.seal_values_through(r,10)
        with self.assertRaises(ValueError): t.add_point(Point(r,5,False))
        self.assertTrue(_tri(CompareValue(r,Compare.EQ,True),5,t,self.registry))
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.SATISFIED)
        false= self.trace(10); false.add_point(Point(r,0,False)); false.add_point(Point(r,10,False))
        eventual=TemporalConstraint("never-held",TemporalOp.EVENTUALLY,CompareValue(r,Compare.EQ,True),Window(0,10))
        self.assertEqual(evaluate(eventual,false,self.registry)[0].verdict,Verdict.INDETERMINATE)
        false.seal_values_through(r,10)
        self.assertEqual(evaluate(eventual,false,self.registry)[0].verdict,Verdict.VIOLATED)

    def test_trigger_first_each_freezes_distinct_occurrences_and_never_retriggers(self):
        r=ValueRef("world.quest_phase","1",{"quest":self.quest})
        for occurrence,expected in ((Occurrence.FIRST,1),(Occurrence.EACH,2)):
            t=self.trace(4)
            t.add_event(Event("e1","belief_revision",1,1,{"actor":"actor-1"}))
            t.add_event(Event("e2","belief_revision",2,2,{"actor":"actor-1"}))
            t.seal_events_through(2)
            t.add_point(Point(r,1,"PLANNED")); t.add_point(Point(r,2,"ACTIVE"))
            c=TemporalConstraint("phase",TemporalOp.EVENTUALLY,CompareValue(r,Compare.IN,("ACTIVE","COMPLETE")),Window(0,1),trigger=Trigger("belief_revision","1",{"actor":"actor-1"},occurrence))
            result=evaluate(c,t,self.registry)
            self.assertEqual(len(result),expected)
            self.assertEqual(result[0].activation_id,"e1")
            self.assertEqual(result[-1].activation_id,"e2" if expected==2 else "e1")
            self.assertEqual(evaluate(c,t,self.registry),result)

    def test_event_missing_coverage_not_activated_vs_indeterminate_and_dedup(self):
        r=ValueRef("world.quest_phase","1",{"quest":self.quest})
        triggered=TemporalConstraint("triggered",TemporalOp.EVENTUALLY,
            CompareValue(r,Compare.EQ,"ACTIVE"),Window(0,1),trigger=Trigger("secret","1"))
        unsealed=self.trace(1)
        self.assertEqual(evaluate(triggered,unsealed,self.registry)[0].verdict,Verdict.INDETERMINATE)
        unsealed.finalize_events()
        self.assertEqual(evaluate(triggered,unsealed,self.registry)[0].verdict,Verdict.NOT_ACTIVATED)
        c=EventCount("once","secret","1",Window(0,2),minimum=1)
        t=self.trace(2)
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.INDETERMINATE)
        t.finalize_events()
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.VIOLATED)
        t2=self.trace(1); e=Event("e","secret",1,1)
        t2.add_event(e); t2.add_event(e)
        self.assertEqual(len(t2.events),1)
        with self.assertRaises(ValueError): t2.add_event(Event("e","other",1,1))
        t3=self.trace(2); t3.add_event(Event("later","x",2,2))
        with self.assertRaises(ValueError): t3.add_event(Event("earlier","x",1,1))

    def test_event_order_requires_distinct_instances_and_complete_ledger(self):
        c=EventOrder("reveal-after","clue","1","reveal","1",StrictOrder.PHYSICAL_TIME,Window(0,5))
        t=self.trace(5); t.add_event(Event("same","clue",2,1)); t.finalize_events()
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.VIOLATED)
        t2=self.trace(5); t2.add_event(Event("c","clue",1,1)); t2.add_event(Event("r","reveal",2,2)); t2.finalize_events()
        self.assertEqual(evaluate(c,t2,self.registry)[0].verdict,Verdict.SATISFIED)

    def test_event_payloads_are_checked_against_pinned_registry(self):
        c=EventCount("destroy","item_destroyed","1",Window(0,2))
        bad_payload=self.trace(2); bad_payload.add_event(Event("bad","item_destroyed",1,1,{"item":"ledger-1"})); bad_payload.finalize_events()
        with self.assertRaises(TypeError): evaluate(c,bad_payload,self.registry)
        extra=self.trace(2); extra.add_event(Event("extra","secret",1,1,{"unexpected":"x"})); extra.finalize_events()
        with self.assertRaises(ValueError): evaluate(EventCount("secret","secret","1",Window(0,2)),extra,self.registry)
        wrong_version=self.trace(2); wrong_version.add_event(Event("v2","item_destroyed",1,1,{"item":self.item},version="2")); wrong_version.finalize_events()
        with self.assertRaises(ValueError): evaluate(c,wrong_version,self.registry)
        wrong_provenance=self.trace(2); wrong_provenance.add_event(Event("obs","item_destroyed",1,1,{"item":self.item},provenance="delivered_observation")); wrong_provenance.finalize_events()
        with self.assertRaises(ValueError): evaluate(c,wrong_provenance,self.registry)

    def test_pointwise_boolean_temporal_semantics_unknown_masking(self):
        p=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item})
        q=ValueRef("actor.belief","1",{"actor":self.actor,"proposition":"secret"})
        t=self.trace(1); t.add_point(Point(p,0,True)); t.add_point(Point(q,0,False)); t.add_point(Point(p,1,False)); t.add_point(Point(q,1,True))
        t.seal_values_through(p,1); t.seal_values_through(q,1)
        c=TemporalConstraint("not-distributive",TemporalOp.EVENTUALLY,And((CompareValue(p,Compare.EQ,True),CompareValue(q,Compare.EQ,True))),Window(0,1))
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.VIOLATED) # F(p AND q), not Fp AND Fq
        t2=self.trace(0); t2.add_point(Point(p,0,True))
        c2=TemporalConstraint("or-mask",TemporalOp.AT,Or((CompareValue(q,Compare.EQ,True),CompareValue(p,Compare.EQ,True))),Window(0,0))
        self.assertEqual(evaluate(c2,t2,self.registry)[0].verdict,Verdict.SATISFIED)

    def test_polynomial_interior_extremum_and_generic_bounds_uncertainty(self):
        ref=self.anxiety
        c=TemporalConstraint("interior",TemporalOp.ALWAYS,CompareValue(ref,Compare.LE,NumericLiteral(F(4,5),"control_unit")),Window(0,1))
        t=self.trace(1); t.add_segment(Segment(ref,0,1,"POLYNOMIAL",(0,4,-4),certificate_id="poly"))
        result=evaluate(c,t,self.registry)[0]
        self.assertEqual(result.verdict,Verdict.VIOLATED)
        self.assertEqual(result.witness,F(1,2))
        t2=self.trace(1); t2.add_segment(Segment(ref,0,1,"BOUNDS",lower=0,upper=1,certificate_id="loose"))
        self.assertEqual(evaluate(c,t2,self.registry)[0].verdict,Verdict.INDETERMINATE)

    def test_continuous_future_gap_open_root_and_degree_zero(self):
        ref=self.anxiety
        c=TemporalConstraint("future",TemporalOp.EVENTUALLY,CompareValue(ref,Compare.GE,NumericLiteral(F(1,2),"control_unit")),Window(5,10))
        self.assertEqual(evaluate(c,self.trace(0),self.registry)[0].verdict,Verdict.PENDING)
        c2=TemporalConstraint("uncertified-gap",TemporalOp.EVENTUALLY,CompareValue(ref,Compare.GE,NumericLiteral(F(1,2),"control_unit")),Window(0,2))
        t=self.trace(2); t.add_point(Point(ref,0,0)); t.add_point(Point(ref,2,0))
        self.assertEqual(evaluate(c2,t,self.registry)[0].verdict,Verdict.INDETERMINATE)
        root=TemporalConstraint("excluded-root",TemporalOp.EVENTUALLY,CompareValue(ref,Compare.LE,NumericLiteral(0,"control_unit")),Window(0,1,False,True))
        t2=self.trace(1); t2.add_segment(Segment(ref,0,1,"POLYNOMIAL",(0,1)))
        self.assertEqual(evaluate(root,t2,self.registry)[0].verdict,Verdict.VIOLATED)
        linear=compile_envelope("linear",ref,((F(0),F(0),F(1)),(F(1),F(0),F(1))),unit="control_unit",interpretation=EnvelopeInterpretation.LINEAR)[0]
        t3=self.trace(1); t3.add_segment(Segment(ref,0,1,"POLYNOMIAL",(F(1,2),)))
        self.assertEqual(evaluate(linear,t3,self.registry)[0].verdict,Verdict.SATISFIED)

    def test_bands_weighted_means_and_invalid_overlap(self):
        ref=self.anxiety
        b=NumericBand("band",ref,Window(0,1),0,F(4,5),unit="control_unit")
        t=self.trace(1); t.add_segment(Segment(ref,0,1,"POLYNOMIAL",(0,4,-4)))
        self.assertEqual(evaluate(b,t,self.registry)[0].verdict,Verdict.VIOLATED)
        # Duration weighted: first window mean 0, second mean 1, unequal durations.
        t2=self.trace(5)
        t2.add_segment(Segment(ref,0,1,"POLYNOMIAL",(0,)))
        t2.add_segment(Segment(ref,1,5,"POLYNOMIAL",(1,)))
        mean=TimeWeightedMeanDifference("means",ref,Window(0,1),Window(1,5),-1,"control_unit")
        r=evaluate(mean,t2,self.registry)[0]
        self.assertEqual(r.verdict,Verdict.SATISFIED)
        self.assertEqual(r.witness,(F(0),F(1)))
        with self.assertRaises(ValueError): TimeWeightedMeanDifference("overlap",ref,Window(0,2),Window(1,3),0,"control_unit")

    def test_conflict_proof_is_narrow_and_eventuals_are_not_mistaken_for_always(self):
        ref=self.anxiety
        a=NumericBand("a",ref,Window(0,5),0,F(1,2),unit="control_unit")
        b=NumericBand("b",ref,Window(2,8),F(3,4),1,unit="control_unit")
        status,proof=detect_hard_conflict([a,b])
        self.assertEqual(status,Compatibility.HARD_CONFLICT_PROVEN)
        self.assertEqual(proof.overlap,(F(2),F(5)))
        p=CompareValue(ref,Compare.LE,NumericLiteral(F(1,2),"control_unit"))
        q=CompareValue(ref,Compare.GE,NumericLiteral(F(3,4),"control_unit"))
        x=TemporalConstraint("eventually-a",TemporalOp.EVENTUALLY,p,Window(0,1))
        y=TemporalConstraint("eventually-b",TemporalOp.EVENTUALLY,q,Window(0,1))
        self.assertEqual(detect_hard_conflict([x,y])[0],Compatibility.COMPATIBILITY_UNKNOWN)

    def test_linear_envelope_gaps_dag_and_state_point_clock(self):
        ref=self.anxiety
        bands=compile_envelope("linear",ref,((F(0),F(0),F(1)),(F(2),F(1,2),F(1))),unit="control_unit",interpretation=EnvelopeInterpretation.LINEAR)
        self.assertEqual(bands[0].lower_at_end,F(1,2))
        point=compile_state_point("p",ref,F(1,2),F(10),unit="control_unit")
        self.assertEqual(point.anchor.absolute_time,F(10)); self.assertEqual(point.window.start,F(0))
        t=self.trace(10); t.add_point(Point(ref,10,F(1,2)))
        self.assertEqual(evaluate(point,t,self.registry)[0].verdict,Verdict.SATISFIED)
        dag=compile_event_dag(((EventNode("clue","clue-1"),EventNode("reveal","reveal-1")),),Window(0,10))
        self.assertEqual(dag[0].before_filter,{"event_id":"clue-1"})
        with self.assertRaises(ValueError): compile_event_dag(((EventNode("a","a"),EventNode("b","b")),(EventNode("b","b"),EventNode("a","a"))),Window(0,1))
        self.assertEqual(compile_envelope("gap",ref,((F(0),F(0),F(1)),),unit="control_unit",interpretation=EnvelopeInterpretation.POINT_ONLY)[0].window.end,F(0))
        hold=compile_envelope("hold",ref,((F(0),F(0),F(1)),(F(2),F(0),F(1))),unit="control_unit",interpretation=EnvelopeInterpretation.HOLD)
        self.assertEqual((hold[0].window.start,hold[0].window.end,hold[0].window.right_closed),(F(0),F(2),False))

    def test_checkpoint_fork_is_monitor_bookkeeping_only(self):
        ref=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item})
        c=TemporalConstraint("at",TemporalOp.AT,CompareValue(ref,Compare.EQ,True),Window(0,0))
        t=self.trace(0); t.add_point(Point(ref,0,True))
        parent=MonitorSession(self.registry); parent.evaluate(c,t)
        child=parent.fork(); child.evaluate(TemporalConstraint("other",TemporalOp.AT,CompareValue(ref,Compare.EQ,True),Window(0,0)),t)
        self.assertNotEqual(parent.checkpoint(),child.checkpoint())
        self.assertEqual(parent.checkpoint(),frozenset({("at","@unanchored")}))

    def test_registry_ast_and_event_payload_mappings_are_defensively_frozen(self):
        args={"actor":self.actor,"item":self.item}
        ref=ValueRef("world.holding","1",args)
        args.clear()
        self.assertEqual(set(ref.args),{"actor","item"})
        with self.assertRaises(TypeError): ref.args["actor"]=self.actor
        registry_args={"task":"WorldTask"}
        entry=RegistryEntry("frozen.test","1",Owner.WORLD,"WorldTask",registry_args,TypeSpec(ValueKind.BOOL),"world_holding_v1",(),TimeMode.POINT_ONLY)
        registry_args.clear()
        self.assertEqual(dict(entry.args),{"task":"WorldTask"})
        with self.assertRaises(TypeError): entry.args["task"]="Other"
        payload={"actor":"actor-1"}
        ev=Event("e","belief_revision",1,1,payload)
        payload["actor"]="changed"
        self.assertEqual(ev.args["actor"],"actor-1")
        with self.assertRaises(TypeError): ev.args["actor"]="changed"
        with self.assertRaises(ValueError):
            t=self.trace(1); t.add_event(Event("a","clue",1,1)); t.add_event(Event("b","clue",1,1))
        with self.assertRaises(ValueError):
            t=self.trace(2); t.add_segment(Segment(self.anxiety,0,2,"POLYNOMIAL",(0,))); t.add_segment(Segment(self.anxiety,1,2,"POLYNOMIAL",(0,)))

    def test_golden_json_cases_load_and_replay(self):
        fixture=Path(__file__).parent/"data"/"golden_cases.json"
        data=json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(data["format"],"trajectory-constraints-v0-golden-1")
        for case in data["cases"]:
            with self.subTest(case=case["case_id"]):
                constraint=ast_from_json(case["constraint"])
                trace_data=case["trace"]
                trace=self.trace(trace_data["now"])
                for raw in trace_data["points"]:
                    trace.add_point(Point(constraint.formula.ref,raw["time"],raw["value"]))
                for raw in trace_data["segments"]:
                    trace.add_segment(Segment(constraint.formula.ref,raw["start"],raw["end"],raw["kind"],
                        tuple(raw.get("coefficients",())),raw.get("lower"),raw.get("upper"),raw.get("certificate_id","")))
                result=evaluate(constraint,trace,self.registry)[0]
                self.assertEqual(result.verdict.value,case["expected"]["verdict"])
                expected=case["expected"]["witness"]
                self.assertEqual(result.witness,F(expected) if expected is not None else None)

    def test_acceptance_manifest_names_real_tests(self):
        manifest=json.loads((Path(__file__).parents[1]/"acceptance_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format"],"trajectory-constraints-v0-acceptance-1")
        names={name for name in dir(type(self)) if name.startswith("test_")}
        mapped={name for row in manifest["admissions"] for name in row["tests"]}
        self.assertTrue(mapped)
        self.assertEqual(mapped-names,set())

    def test_exhaustive_kleene_not_and_or_tables(self):
        values=(True,False,None)
        def kleene_and(xs): return False if False in xs else None if None in xs else True
        def kleene_or(xs): return True if True in xs else None if None in xs else False
        p=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item})
        q=ValueRef("actor.belief","1",{"actor":self.actor,"proposition":"p"})
        formulas=(
            lambda a,b: And((CompareValue(p,Compare.EQ,True),CompareValue(q,Compare.EQ,True))),
            lambda a,b: Or((CompareValue(p,Compare.EQ,True),CompareValue(q,Compare.EQ,True))),
        )
        for a in values:
            for b in values:
                t=self.trace(0)
                if a is not None: t.add_point(Point(p,0,a))
                if b is not None: t.add_point(Point(q,0,b))
                atoms=(CompareValue(p,Compare.EQ,True),CompareValue(q,Compare.EQ,True))
                self.assertEqual(_tri(Not(atoms[0]),0,t,self.registry),None if a is None else not a)
                self.assertEqual(_tri(formulas[0](a,b),0,t,self.registry),kleene_and((a,b)))
                self.assertEqual(_tri(formulas[1](a,b),0,t,self.registry),kleene_or((a,b)))

    def test_time_shift_invariance_for_at_eventually_and_always(self):
        ref=ValueRef("world.holding","1",{"actor":self.actor,"item":self.item})
        def run(shift,op):
            t=self.trace(shift+2)
            t.add_point(Point(ref,shift,False)); t.add_point(Point(ref,shift+1,True)); t.add_point(Point(ref,shift+2,True))
            window=Window(0,0) if op is TemporalOp.AT else Window(0,2)
            c=TemporalConstraint("shift",op,CompareValue(ref,Compare.EQ,True),window,Anchor(AnchorKind.FIXED_ABSOLUTE,absolute_time=shift))
            return evaluate(c,t,self.registry)[0]
        for op in (TemporalOp.AT,TemporalOp.EVENTUALLY,TemporalOp.ALWAYS):
            first,second=run(0,op),run(7,op)
            self.assertEqual(first.verdict,second.verdict)
            if isinstance(first.witness,type(F(1))): self.assertEqual(second.witness,first.witness+7)

    def test_mean_invariant_under_certificate_splitting(self):
        ref=self.anxiety
        c=TimeWeightedMeanDifference("split-mean",ref,Window(0,2),Window(2,5),0,"control_unit")
        whole=self.trace(5); whole.add_segment(Segment(ref,0,5,"POLYNOMIAL",(1,)))
        split=self.trace(5); split.add_segment(Segment(ref,0,2,"POLYNOMIAL",(1,))); split.add_segment(Segment(ref,2,5,"POLYNOMIAL",(1,)))
        self.assertEqual(evaluate(c,whole,self.registry)[0].verdict,evaluate(c,split,self.registry)[0].verdict)

    def test_trace_certificates_must_match_registered_time_mode_and_value_kind(self):
        holding=Trace(now=1); holding.add_segment(Segment(self.holding,0,1,"POLYNOMIAL",(0,)))
        c=TemporalConstraint("holding",TemporalOp.ALWAYS,CompareValue(self.holding,Compare.EQ,True),Window(0,1))
        with self.assertRaises(TypeError): evaluate(c,holding,self.registry)
        step=ValueRef("world.progress","1",{"task":StableEntity("WorldTask","task-1")})
        nonconstant=Trace(now=1); nonconstant.add_segment(Segment(step,0,1,"POLYNOMIAL",(0,F(1,2))))
        with self.assertRaises(ValueError): evaluate(NumericBand("step-band",step,Window(0,1),0,1,unit="fraction"),nonconstant,self.registry)

    def test_dispatch_runs_only_typed_pure_projector_and_monitor_stays_separate_from_reachability(self):
        task=ValueRef("world.progress","1",{"task":StableEntity("WorldTask","task-1")})
        entry=self.registry.resolve(task.observable_id,task.version)
        result=project_registered(entry,{"tasks":{"task-1":{"effort_done":"1","effort_target":"2"}}},task.args)
        self.assertTrue(result.known); self.assertEqual(result.value,F(1,2))
        invalid=project_registered(entry,{"tasks":{"task-1":{"effort_done":"3","effort_target":"2"}}},task.args)
        self.assertFalse(invalid.known)
        no_fallback=project_registered(entry,{"tasks":{"another-task":{"effort_done":"1","effort_target":"2"}},"effort_done":"1","effort_target":"1"},task.args)
        self.assertFalse(no_fallback.known)
        event_entry=self.registry.resolve("secret","1")
        incomplete_ledger=project_registered(event_entry,{"ledger_events_complete":False,"ledger_events":[]},{})
        self.assertFalse(incomplete_ledger.known)
        c=TemporalConstraint("goal",TemporalOp.EVENTUALLY,CompareValue(self.holding,Compare.EQ,True),Window(0,5))
        t=self.trace(1); t.add_point(Point(self.holding,0,False)); t.add_point(Point(self.holding,1,False))
        t.add_event(Event("destroy-1","item_destroyed",1,1,{"item":self.item}))
        t.seal_values_through(self.holding,1)
        self.assertEqual(evaluate(c,t,self.registry)[0].verdict,Verdict.PENDING)

    def test_explicit_migration_replay_gate(self):
        oldref=ValueRef("world.progress","1",{"task":StableEntity("WorldTask","t")})
        old=TemporalConstraint("old",TemporalOp.AT,CompareValue(oldref,Compare.GE,NumericLiteral(0,"fraction")),Window(0,0))
        new_registry=Registry(self.registry.entries()+(RegistryEntry("world.progress","2",Owner.WORLD,"WorldTask",{"task":"WorldTask"},TypeSpec(ValueKind.REAL,"fraction",lower=0,upper=1),"task_progress_fraction_v1",("done","target"),TimeMode.PIECEWISE_CONSTANT),))
        new=TemporalConstraint("new",TemporalOp.AT,CompareValue(ValueRef("world.progress","2",oldref.args),Compare.GE,NumericLiteral(0,"fraction")),Window(0,0))
        verify_migration("1","2",[old],[new],new_registry,lambda a,b:True)
        with self.assertRaises(ValueError): verify_migration("1","2",[old],[new],new_registry,lambda a,b:False)


if __name__ == "__main__": unittest.main()
