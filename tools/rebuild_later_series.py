#!/usr/bin/env python3
"""Rebuild the scoped later-series delivery, retaining command results."""
import concurrent.futures,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'docs/later-series-upgrade-2026-09-07'
def run(row):
 p=ROOT/row['deck'];out=p/'build/checks';out.mkdir(parents=True,exist_ok=True);records=[]
 commands=[('build',[sys.executable,'tools/build_deck.py',row['deck']]),('lint',[sys.executable,'tools/lint_deck_text.py',row['deck'],'--json',str(p/'lint.json')]),('layout',[sys.executable,'tools/check_layout.py',row['deck'],'--no-build','--json',str(p/'layout.json')]),('preview',[sys.executable,'tools/preview_deck.py',row['deck']]),('contact',[sys.executable,'tools/contact_sheet.py',row['deck']]),('svg-fonts',[sys.executable,'tools/check_svg_fonts.py',row['deck'],'--json',str(p/'svg-fonts.json')])]
 for name,cmd in commands:
  r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/f'{name}.log').write_text(r.stdout);records.append({'name':name,'exit':r.returncode})
  if r.returncode: print(row['deck'],name,'FAILED',r.stdout[-1600:],flush=True);break
 report={'deck':row['deck'],'commands':records,'passed':len(records)==len(commands) and all(x['exit']==0 for x in records)}
 print(row['deck'],report['passed'],flush=True);return report
if __name__=='__main__':
 rows=json.loads((HERE/'status.json').read_text())['topics']
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,rows))
 (HERE/'gate-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 sys.exit(0 if all(r['passed'] for r in results) else 1)
