#!/usr/bin/env python3
"""Build a versioned non-duplicate analysis view without mutating lossless source."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from command_schema_v0 import canonical_verb_family
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixture',type=Path); ap.add_argument('out',type=Path); a=ap.parse_args(); rows=[json.loads(x) for x in a.fixture.open(encoding='utf-8') if x.strip()]
    kept=[]; excluded=[]; categories={k:0 for k in ('EXACT_DUPLICATE_PAIR','ACTION_REPEAT_ONLY','OBSERVATION_REPEAT_ONLY','GENUINE_TRANSITION')}
    for r in rows:
        h=r.get('history',[]); p=h[-1] if h else None
        if not p: kept.append(r); categories['GENUINE_TRANSITION']+=1; continue
        so=r['source_O']==p['source_O']; sr=r['source_action_A_star']==p['source_action_A_star']
        if so and sr: excluded.append(r); categories['EXACT_DUPLICATE_PAIR']+=1
        elif (not so) and sr: kept.append(r); categories['ACTION_REPEAT_ONLY']+=1
        elif so and (not sr): kept.append(r); categories['OBSERVATION_REPEAT_ONLY']+=1
        else: kept.append(r); categories['GENUINE_TRANSITION']+=1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('w',encoding='utf-8',newline='\n') as f:
        for r in kept: f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    manifest={'schema_version':'clubfloyd_stage0c_analysis_view_v0','source_fixture_sha256':hashlib.sha256(a.fixture.read_bytes()).hexdigest(),'view_rule':'exclude only rows whose target (source_O, source_action_A_star) exactly equals immediately previous history pair; preserve all other rows and raw source','input_rows':len(rows),'output_rows':len(kept),'excluded_exact_duplicate_rows':len(excluded),'category_counts_input':categories,'view_sha256':hashlib.sha256(a.out.read_bytes()).hexdigest(),'lossless_source_unchanged':True}
    a.out.with_suffix('.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
