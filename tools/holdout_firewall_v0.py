#!/usr/bin/env python3
"""One-shot holdout report. It refuses to perform search after holdout."""
import argparse,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--baseline-train',type=Path,required=True); ap.add_argument('--selected-train',type=Path); ap.add_argument('--baseline-holdout',type=Path,required=True); ap.add_argument('--selected-holdout',type=Path); ap.add_argument('--no-selection',action='store_true'); ap.add_argument('--selection-frozen',action='store_true'); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--source-revision',default='unknown'); a=ap.parse_args()
    if not a.selection_frozen: raise SystemExit('refusing holdout: selection must be frozen before access')
    result={'schema_version':'character_dynamics_holdout_firewall_v0','baseline_train':load(a.baseline_train),'selected_train':None if a.no_selection else load(a.selected_train),'baseline_holdout':load(a.baseline_holdout),'selected_holdout':None if a.no_selection else load(a.selected_holdout),'selection':'BASELINE_RETAINED / NO_SELECTION' if a.no_selection else 'selected_candidate','selection_frozen_before_holdout':True,'search_after_holdout_performed':False,'provenance':{'source_revision':a.source_revision}}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
