"""Check deliverable links, excluding literal Markdown examples in manuscripts."""
from pathlib import Path
import re,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
rows=json.loads((HERE/'status.json').read_text())['topics']
files=[HERE/'README.md']+[ROOT/r['deck']/n for r in rows for n in ['README.md','manuscript.md','source-map.md']]
missing=[];checked=0
for f in files:
 out=[];fenced=False
 for line in f.read_text().splitlines():
  if line.startswith('```'):fenced=not fenced;continue
  if not fenced:out.append(line)
 for target in re.findall(r'(?<!\\)\[[^\]]*(?<!\\)\]\(([^)]+)\)','\n'.join(out)):
  target=target.split('#')[0]
  if not target or target.startswith(('https://','http://','mailto:')):continue
  checked+=1
  if not (f.parent/target).exists():missing.append({'file':str(f.relative_to(ROOT)),'target':target})
(HERE/'links.json').write_text(json.dumps({'links_checked':checked,'code_examples_excluded':True,'missing':missing},ensure_ascii=False,indent=2)+'\n')
print(checked,'links;',len(missing),'missing')
raise SystemExit(bool(missing))
