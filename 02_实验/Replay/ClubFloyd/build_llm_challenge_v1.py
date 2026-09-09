#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('source',type=Path); ap.add_argument('out',type=Path); args=ap.parse_args()
    rows=[]
    for line in args.source.open(encoding='utf-8'):
        x=json.loads(line); rows.append({'audit_id':x['audit_id'],'raw_action':x['raw_action'],'pre_action_state':x['pre_action_state']})
    with args.out.open('w',encoding='utf-8',newline='\n') as f:
        for x in rows: f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'schema_version':'command_admission_llm_challenge_v1','rows':len(rows),'sha256':hashlib.sha256(args.out.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
