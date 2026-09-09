#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
def seeds(p):
    text=(Path(p)/'metadata.txt').read_text(encoding='utf-8');m=re.search(r'world_scenario_seeds=([^\n]+)',text);return [int(x) for x in m.group(1).split(',')] if m else []
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--train',type=Path,required=True);ap.add_argument('--holdout',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-revision',default='unknown');a=ap.parse_args();ts=seeds(a.train);hs=seeds(a.holdout);r={'schema_version':'character_dynamics_development_split_audit_v1','train_world_seeds':ts,'holdout_world_seeds':hs,'overlap':sorted(set(ts)&set(hs)),'pass':bool(ts and hs and not(set(ts)&set(hs))),'train_metadata':str(a.train/'metadata.txt'),'holdout_metadata':str(a.holdout/'metadata.txt'),'provenance':{'source_revision':a.source_revision}};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
if __name__=='__main__':main()
