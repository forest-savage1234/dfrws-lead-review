"""Build an offline display of an executed presenter trace; no engine runs in HTML."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>DFRWS fictional journey — recorded execution</title>
<style>body{margin:0;background:#f2f5f4;color:#173f3b;font:18px/1.5 Arial,sans-serif}main{max-width:1050px;margin:auto;padding:30px}h1{font-size:32px;line-height:1.2}h2{font-size:24px}.notice{background:#173f3b;color:white;padding:16px}.small{font-size:15px}nav{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}button{font:inherit;padding:10px;background:white;color:#173f3b;border:2px solid #376e60;cursor:pointer}button[aria-pressed=true]{background:#376e60;color:white}button:focus-visible{outline:4px solid #df9800}section{padding:22px;background:white}dt{font-weight:bold;margin-top:12px}dd{margin:0;overflow-wrap:anywhere}pre{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}</style></head>
<body><main><h1>A corrected time and an earlier decision</h1>
<p class="notice"><strong>Recorded execution; fictional records.</strong> These controls display captured output. They do not execute the engine or change a decision.</p>
<p>For this proposed school-to-stop journey, departure must precede the sighting. Identity, travel feasibility and source reliability remain unresolved.</p>
<nav aria-label="Recorded stages"><button data-stage="0">1. Earlier decision</button><button data-stage="1">2. Correction</button><button data-stage="2">3. Simulated review</button><button data-stage="3">4. Further correction</button><button data-stage="4">5. Unrelated edit</button><button data-stage="5">6. Editorial edit</button><button data-stage="6">7. Missing relationship</button></nav>
<section id="stage" aria-live="polite"></section>
<details><summary>Inspect the full captured trace</summary><pre id="full"></pre></details>
<p class="small">This separately named presenter example is outside the original 16-case ledger benchmark and earlier 24-scenario snapshot study. The later benchmark retains two missing-link misses. No practitioner benefit or authenticated custody is established.</p>
<p class="small">CaseLinker was created and is maintained by Mrinaal Ramachandran and contributors. Forest Savage contributed merged PR #6 and PR #7. This separate ledger preserves reused model attribution and MIT licensing.</p>
<p class="small">Replay commands and complete licenses are in the accompanying source ZIP. The HTML embeds the exact trace and license text; it loads no remote resources.</p>
<details><summary>License and reused model provenance</summary><pre id="licenses"></pre></details>
</main><script type="application/json" id="trace">__TRACE__</script>
<script type="application/json" id="license-data">__LICENSES__</script>
<script>
const t=JSON.parse(document.getElementById('trace').textContent),runs=t.runs,j=runs[0],after=j.after;
const d1=after.nodes.find(n=>n.id==='decision_d1'),d2=after.nodes.find(n=>n.id==='decision_d2');
const box=document.getElementById('stage');
function item(label,value){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=typeof value==='string'?value:JSON.stringify(value);box.append(dt,dd)}
function heading(title,body){const h=document.createElement('h2'),p=document.createElement('p');h.textContent=title;p.textContent=body;box.append(h,p)}
function request(r){item('Decision selected',r.decision_id);item('Earlier reason',r.original_rationale);item('Earlier / corrected event time',r.old_values.event_time+' / '+r.new_values.event_time);item('Registered path',r.dependency_path.join(' → '));item('Engine conclusion',r.conclusion)}
function show(n){box.replaceChildren();
if(n===0){heading('1. D1: a conditional journey is set aside','Same date and +08:00 offset: school departure 15:10; bus-stop sighting 14:40. The reason applies to this proposed journey.');item('Recorded decision',d1.disposition);item('Reason',d1.rationale);item('Supplied field scope','School and bus event_time');}
if(n===1){heading('2. The corrected time selects D1 for review','The sighting changes to 15:40. The engine follows a recorded relationship; D1 remains unchanged.');request(j.events[0].new_requests[0]);}
if(n===2){heading('3. A simulated person appends D2','This is a captured actor action. The actor label is not authentication.');item('D1 retained',d1.rationale);item('D2 disposition',d2.disposition);item('D2 reason',d2.rationale);item('D2 supersedes',d2.supersedes);item('Actor authority',after.human_reviews[0].authority);}
if(n===3){heading('4. A further correction targets D2','The later sighting becomes 16:00 +08:00. The active successor receives another review request.');request(j.events[2].new_requests[0]);item('Internal integrity',after.integrity);}
if(n>=4){const r=runs[n-3],e=r.events[0];heading(['5. An unrelated source changes','6. An editorial field changes','7. The needed relationship is absent'][n-4],n===6?'A required request is missed. The known coverage warning cannot restore the relationship. Entirely unrecorded dependencies can remain invisible.':'The capture is retained, but it does not change the relevant time dependency.');item('Observed new requests',e.new_requests.length);item('Coverage',e.coverage);item('Retained D1',r.after.nodes.find(x=>x.id==='decision_d1').rationale);item('Internal integrity',r.after.integrity.status);}
document.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.stage)===n?'true':'false'));}
document.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>show(Number(b.dataset.stage))));
document.getElementById('full').textContent=JSON.stringify(t,null,2);document.getElementById('licenses').textContent=JSON.parse(document.getElementById('license-data').textContent);show(0);
</script></body></html>'''


def safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, default=ROOT / 'presenter/PRESENTER_Trace.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'PRESENTER_Recorded_Viewer.html')
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    licenses = '\n\n'.join((ROOT / name).read_text(encoding='utf-8') for name in ['LICENSE', 'lead_review/vendor/LICENSE', 'lead_review/vendor/PROVENANCE.json'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(TEMPLATE.replace('__TRACE__', safe_json(trace)).replace('__LICENSES__', safe_json(licenses)), encoding='utf-8', newline='\n')
    print('Built recorded presenter viewer with embedded trace and complete licenses; no browser verification performed.')


if __name__ == '__main__':
    main()
