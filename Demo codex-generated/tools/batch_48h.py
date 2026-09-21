"""Generate the frozen 128-actor Demo Living 48h application diagnostic."""
import csv, json, math, pathlib, shutil, subprocess, sys, statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "demo/living_dynamics_v0/batch_48h_v0"
MODEL_ID = "demo-living-v0"
BATCH_ID = "demo-living-v0"
CONFIG_VERSION = "demo-living-v1-calibration-pass-1"
PROFILES = ["balanced", "disciplined", "procrastinating", "rest_seeking", "stimulation_seeking", "anxious", "body_sensitive", "spontaneous"]
PROFILE_VALUES = {
    "balanced": [.5]*8, "disciplined": [.2,.8,.4,.35,.4,.5,.6,.25],
    "procrastinating": [.8,.3,.5,.7,.65,.5,.5,.55], "rest_seeking": [.5,.45,.8,.4,.45,.5,.65,.35],
    "stimulation_seeking": [.65,.4,.35,.85,.45,.5,.45,.65], "anxious": [.55,.5,.55,.5,.85,.55,.65,.4],
    "body_sensitive": [.45,.55,.6,.4,.5,.65,.9,.35], "spontaneous": [.5,.45,.5,.65,.5,.5,.5,.9],
}
def run(exe, actor, path):
    profile = PROFILES[actor % 8]; scenario = 1000 + actor*17; policy = 5000 + actor*31
    subprocess.run([exe, str(scenario), str(policy), str(path)], check=True, stdout=subprocess.DEVNULL)
    data = json.loads(path.read_text()); assert data[-1]["timestamp"] >= 3360
    assert all(f["dynamics_model"] == MODEL_ID and f["demo_only"] for f in data)
    assert all(f["timestamp"] > data[i-1]["timestamp"] for i,f in enumerate(data) if i)
    assert all(math.isfinite(f["state"][k]) and 0 <= f["state"][k] <= 1 for f in data for k in ("hunger","fatigue","bathroom_urge","boredom","task_pressure","satisfaction","anxiety","screen_strain"))
    return data, profile, scenario, policy
def action_name(f):
    a=f.get("running_action_before")
    return a.get("action") if isinstance(a,dict) else None
def outcome_successes(data, name):
    return sum(1 for f in data for key in ("pre_policy_outcome","post_policy_outcome") if isinstance(f.get(key),dict) and f[key].get("accepted") and f[key].get("action")==name)
def max_episode(data, key, threshold, high=True):
    best=cur=0
    for f in data:
        hit=f["state"][key]>=threshold if high else f["state"][key]<=threshold
        cur=cur+f["elapsed"] if hit else 0; best=max(best,cur)
    return best
def compact(f, profile, scenario, policy):
    s=f["state"]; ra=f.get("running_action_after") or {}; rb=f.get("running_action_before") or {}
    return {"actor_id":f["actor_id"],"profile":profile,"scenario_seed":scenario,"policy_seed":policy,"dynamics_model":MODEL_ID,"timestamp":f["timestamp"],"day":(f["timestamp"]-480)//1440+1,"clock":f["timestamp"]%1440,"elapsed_minutes":f["elapsed"],"selected_action":f.get("selected_action"),"selected_target":f.get("selected_target",""),"running_action_before":rb.get("action") if rb else None,"running_action_after":ra.get("action") if ra else None,**{k:s[k] for k in ("hunger","fatigue","bathroom_urge","boredom","task_pressure","satisfaction","anxiety","screen_strain")},"task_effort":f.get("task_effort",0),"effort_target":f.get("effort_target"),"commitment_status":f.get("commitment_status"),"decision_gate_reasons":f.get("decision_gate",{}).get("reasons",[]),"validation_result":f.get("validation",{}),"rejection_reason":(f.get("post_policy_outcome") or {}).get("failure_reason") if f.get("post_policy_outcome") else None,"top3_policy_candidates":[{"action":x["action"],"target":x.get("target",""),"probability":x.get("probability",0)} for x in sorted(f.get("candidates",[]),key=lambda x:x.get("probability",0),reverse=True)[:3]]}
def summary(actor, profile, scenario, policy, data):
    acts=[f.get("selected_action") for f in data if f.get("selected_action")]; mins={a:sum(f["elapsed"] for f in data if action_name(f)==a) for a in set(action_name(f) for f in data if action_name(f))}
    # A policy sample that deliberately keeps the current RunningAction is a
    # reconsideration, not a behavioral switch.  Count actual action starts.
    running_after=[(f.get("running_action_after") or {}).get("action") for f in data]
    starts=[]
    previous=None
    for action in running_after:
        if action and action != previous: starts.append(action)
        previous=action
    def vals(k): return [f["state"][k] for f in data]
    switches=sum(a!=b for a,b in zip(starts,starts[1:])); entropy=-sum((n/sum(mins.values()))*math.log(n/sum(mins.values())) for n in mins.values() if n)
    flags=[]; sleep=mins.get("sleep_at_bed",0)+mins.get("sleep",0); meals=outcome_successes(data,"get_meal"); baths=outcome_successes(data,"go_to_bathroom")
    if sleep==0: flags.append("NO_SLEEP_48H")
    if sleep>960: flags.append("EXCESSIVE_SLEEP")
    if meals/2>6: flags.append("MEAL_SPAM")
    if baths/2>10: flags.append("BATHROOM_SPAM")
    nonboot=sum(n for a,n in mins.items() if a not in ("idle",));
    if nonboot and max(mins.values())/nonboot>.75: flags.append("ACTION_COLLAPSE")
    waking=max(1,sum(mins.values())-sleep)
    if sum(n for a,n in mins.items() if a and "study" in a)/waking>.75: flags.append("STUDY_LOCK")
    if sum(mins.get(a,0) for a in ("use_phone","use_computer"))/waking>.75: flags.append("LEISURE_LOCK")
    for key in ("hunger","fatigue","bathroom_urge","boredom","task_pressure","satisfaction","anxiety","screen_strain"):
        hi=max_episode(data,key,.98); lo=max_episode(data,key,.02,False)
        if hi>=240: flags.append(f"{key.upper()}_HIGH_SATURATION")
        # Screen strain is an exposure load, so an absent screen dose is not a
        # psychological low-saturation failure.  Its executable invariant is
        # response to real screen exposure, checked below.
        if lo>=240 and key not in ("satisfaction","screen_strain",): flags.append(f"{key.upper()}_LOW_SATURATION")
    screen_minutes=sum(mins.get(a,0) for a in ("use_phone","shop_on_phone","use_computer","study_at_computer"))
    if screen_minutes>=120 and max(vals("screen_strain"))<.20: flags.append("SCREEN_STRAIN_UNRESPONSIVE")
    if max_episode(data,"hunger",.85)>=120: flags.append("UNMET_HUNGER")
    if max_episode(data,"bathroom_urge",.85)>=90: flags.append("UNMET_BATHROOM")
    rejected=[(f.get("selected_action"),f.get("selected_target","")) for f in data if f.get("validation",{}).get("performed") and not f.get("validation",{}).get("accepted")]
    if any(rejected.count(item)>1 for item in set(rejected)): flags.append("REJECTION_LOOP")
    return {"actor_id":actor,"profile":profile,"scenario_seed":scenario,"policy_seed":policy,"actual_minutes":data[-1]["timestamp"]-480,"boundary_count":len(data),"decision_count":sum(f.get("policy_evaluated",False) for f in data),"study_minutes":sum(n for a,n in mins.items() if "study" in a),"leisure_minutes":sum(n for a,n in mins.items() if a in ("use_phone","use_computer")),"idle_minutes":mins.get("idle",0),"rest_minutes":mins.get("rest_at_bed",0),"sleep_minutes":sleep,"meal_count":meals,"bathroom_count":baths,"phone_count":sum(a=="use_phone" for a in acts),"computer_count":sum(a=="use_computer" for a in acts),"study_action_count":sum("study" in a for a in acts),"unique_actions":len(set(starts)),"action_entropy":round(entropy,6),"switches_per_day":switches/2,"longest_same_action_streak":max((sum(1 for _ in g) for _,g in __import__('itertools').groupby(action_name(f) for f in data)),default=0),"task_final_effort":data[-1].get("task_effort",0),"task_completed":any((f.get("pre_policy_outcome") or {}).get("task_completed") or (f.get("post_policy_outcome") or {}).get("task_completed") for f in data),"task_completion_time":next((f["timestamp"]-480 for f in data if (f.get("pre_policy_outcome") or {}).get("task_completed") or (f.get("post_policy_outcome") or {}).get("task_completed")),""),"hunger_mean":statistics.mean(vals("hunger")),"hunger_max":max(vals("hunger")),"hunger_final":vals("hunger")[-1],"fatigue_mean":statistics.mean(vals("fatigue")),"fatigue_max":max(vals("fatigue")),"fatigue_final":vals("fatigue")[-1],"bathroom_mean":statistics.mean(vals("bathroom_urge")),"bathroom_max":max(vals("bathroom_urge")),"bathroom_final":vals("bathroom_urge")[-1],"boredom_mean":statistics.mean(vals("boredom")),"boredom_max":max(vals("boredom")),"boredom_final":vals("boredom")[-1],"task_pressure_mean":statistics.mean(vals("task_pressure")),"task_pressure_max":max(vals("task_pressure")),"task_pressure_final":vals("task_pressure")[-1],"satisfaction_mean":statistics.mean(vals("satisfaction")),"satisfaction_min":min(vals("satisfaction")),"satisfaction_final":vals("satisfaction")[-1],"anxiety_mean":statistics.mean(vals("anxiety")),"anxiety_max":max(vals("anxiety")),"anxiety_final":vals("anxiety")[-1],"screen_exposure_minutes":screen_minutes,"rejection_count":len(rejected),"diagnostic_flags":"|".join(flags)}
def main():
    global OUT, MODEL_ID, BATCH_ID, CONFIG_VERSION
    exe=sys.argv[1]
    MODEL_ID=sys.argv[2] if len(sys.argv)>2 else MODEL_ID
    if len(sys.argv)>3: OUT=ROOT / sys.argv[3]
    if len(sys.argv)>4: BATCH_ID=sys.argv[4]
    if len(sys.argv)>5: CONFIG_VERSION=sys.argv[5]
    OUT.mkdir(parents=True,exist_ok=True); raw=OUT/".raw"; raw.mkdir(exist_ok=True)
    version="v1" if MODEL_ID.endswith("v1") else "v0"
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT.parent,text=True).strip()
    manifest={"milestone":f"DEMO_LIVING_BATCH_48H_{version.upper()}","artifact_id":BATCH_ID,"actors":128,"profiles":PROFILES,"seeds":{"scenario":"1000 + actor_id * 17","policy":"5000 + actor_id * 31"},"start_total_minutes":480,"horizon_minutes":2880,"dynamics_model":MODEL_ID,"git_revision":revision,"config_version":CONFIG_VERSION,"demo_only":True}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n"); (OUT/"profiles.json").write_text(json.dumps({k:{"values":v,"classification":"demo engineering profile"} for k,v in PROFILE_VALUES.items()},indent=2)+"\n")
    rows=[]; compact_lines=[]; traces={}
    for actor in range(128):
        path=raw/f"actor_{actor:03d}.json"; data,profile,sc,ps=run(exe,actor,path); [f.update(actor_id=actor) for f in data]; traces[actor]=data; rows.append(summary(actor,profile,sc,ps,data)); compact_lines.extend(json.dumps(compact(f,profile,sc,ps),separators=(",",":")) for f in data)
    fields=list(rows[0]);
    with (OUT/"actor_summary.csv").open("w",newline="") as h: w=csv.DictWriter(h,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with (OUT/"compact_traces.jsonl").open("w") as h: h.write("\n".join(compact_lines)+"\n")
    for profile in PROFILES:
        candidates=[r for r in rows if r["profile"]==profile]; med=min(candidates,key=lambda r:sum(abs(r[k]-statistics.median(x[k] for x in candidates)) for k in ("study_minutes","leisure_minutes","sleep_minutes","action_entropy","switches_per_day"))); anom=max(candidates,key=lambda r:(len(r["diagnostic_flags"].split("|")) if r["diagnostic_flags"] else 0,-r["actor_id"])); (OUT/"representative_traces").mkdir(exist_ok=True); (OUT/"representative_traces"/f"{profile}_representative.json").write_text(json.dumps(traces[med["actor_id"]],indent=2)+"\n"); (OUT/"representative_traces"/f"{profile}_anomalous.json").write_text(json.dumps(traces[anom["actor_id"]],indent=2)+"\n")
    flag_counts={}; [flag_counts.__setitem__(flag,flag_counts.get(flag,0)+1) for r in rows for flag in set(filter(None,r["diagnostic_flags"].split("|")))]; switch_values=[float(r["switches_per_day"]) for r in rows]; aggregate={"actors":len(rows),"actor_hours":len(rows)*48,"total_boundaries":sum(r["boundary_count"] for r in rows),"diagnostic_counts":flag_counts,"switching_distribution":{"median":statistics.median(switch_values),"p90":sorted(switch_values)[round(.9*(len(switch_values)-1))],"p95":sorted(switch_values)[round(.95*(len(switch_values)-1))],"max":max(switch_values)}}; (OUT/"aggregate.json").write_text(json.dumps(aggregate,indent=2)+"\n")
    # Determinism audit is intentionally independent of the first pass.
    for actor in range(128):
        check=raw/f"actor_{actor:03d}_rerun.json"; run(exe, actor, check)
        original=raw/f"actor_{actor:03d}.json"
        if original.read_bytes()!=check.read_bytes(): raise SystemExit(f"non-deterministic actor {actor}")
    shutil.rmtree(raw)
    (OUT/"BATCH_48H_REPORT.md").write_text(f"# DEMO_LIVING_BATCH_48H_{version.upper()}\n\nDemo/application engineering diagnostic. Not research evidence and not a claim of psychological realism.\n\n- Artifact: `{BATCH_ID}`.\n- 128 independent actors, 8 demo engineering profiles × 16 seeds.\n- 48 simulated hours each; total 6144 actor-hours.\n- Dynamics model: `{MODEL_ID}`.\n- Selection: per profile, nearest multidimensional median and highest diagnostic count (actor_id tie-break).\n- Full raw traces remain local-only; compact audit trace contains every boundary.\n\nSee `actor_summary.csv`, `profile_summary.csv` (generated with this batch runner), `aggregate.json`, and `representative_traces/`.\n")
    report=(OUT/"BATCH_48H_REPORT.md").read_text(); report += "\n## Behavior distribution\n\n" + "\n".join(f"- {k}: {sum(r[k] for r in rows):.1f} minutes" for k in ("study_minutes","leisure_minutes","idle_minutes","rest_minutes","sleep_minutes"))
    report += "\n\n## Stability diagnostics\n\n" + "\n".join(f"- {k}: {v} actors" for k,v in sorted(aggregate["diagnostic_counts"].items()))
    report += f"\n\n## Switching distribution\n\n- median: {aggregate['switching_distribution']['median']:.2f}/day\n- p90: {aggregate['switching_distribution']['p90']:.2f}/day\n- p95: {aggregate['switching_distribution']['p95']:.2f}/day\n- max: {aggregate['switching_distribution']['max']:.2f}/day\n"
    report += "\n\n## Representative timelines\n\nSelection is automatic; see the 16 JSON traces for full records.\n"
    (OUT/"BATCH_48H_REPORT.md").write_text(report)
    # compact profile aggregation for quick review
    with (OUT/"profile_summary.csv").open("w",newline="") as h:
        w=csv.writer(h,lineterminator="\n"); w.writerow(["profile","actors","study_hours_day_mean","study_hours_day_p10","study_hours_day_p90","leisure_hours_day_mean","sleep_hours_day_mean","meals_day_mean","task_completion_rate","task_completion_time_p10","task_completion_time_p90","switches_day_mean","action_entropy_mean","diagnostic_count"])
        for p in PROFILES:
            rs=[r for r in rows if r["profile"]==p]; avg=lambda k:statistics.mean(r[k] for r in rs); pct=lambda k,q:sorted(r[k] for r in rs)[max(0,min(15,round(q*15)))]
            times=[r["task_completion_time"] for r in rs if r["task_completion_time"]!=""]; tp=lambda q: sorted(times)[max(0,min(len(times)-1,round(q*(len(times)-1))))] if times else ""; w.writerow([p,16,avg("study_minutes")/60/2,pct("study_minutes",.1)/60/2,pct("study_minutes",.9)/60/2,avg("leisure_minutes")/60/2,avg("sleep_minutes")/60/2,avg("meal_count")/2,avg("task_completed"),tp(.1),tp(.9),avg("switches_per_day"),avg("action_entropy"),sum(bool(r["diagnostic_flags"]) for r in rs)])
if __name__=="__main__": main()
