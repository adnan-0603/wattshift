"""Source-date-aware badge and README update; never turns stale data into live data."""
from datetime import datetime,timezone
from html import escape
import json,re
from pathlib import Path
from zoneinfo import ZoneInfo
from wattshift.simulator import Interval,plan,timestamp
root=Path(__file__).resolve().parents[1]
s=json.loads((root/'apps/console/public/data/console.json').read_text());now=datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('Europe/Berlin')).date()
rows=[r for r in s['prices'] if timestamp(r['start']).astimezone(ZoneInfo('Europe/Berlin')).date()==today]
stale=(now-timestamp(s['retrieved_at'])).total_seconds()>36*3600
message='Data unavailable for today'
if rows:
 start=timestamp(rows[0]['start']);end=timestamp(rows[-1]['end'])
 try:
  p=plan([Interval(timestamp(r['start']),timestamp(r['end']),start,r['price']) for r in rows],decision_at=start,release=start,deadline=end,duration_minutes=240)
  best=p['selected'];a=timestamp(best['start_utc']).astimezone(ZoneInfo('Europe/Berlin')).strftime('%H:%M');b=timestamp(best['end_utc']).astimezone(ZoneInfo('Europe/Berlin')).strftime('%H:%M')
  average=best['energy_cost_eur']/best['energy_kwh']*1000
  message=f'{today} · cheapest 4h {a}–{b} · avg {average:.1f} €/MWh'+(' · STALE' if stale else '')
 except ValueError:message=f'{today} · insufficient complete data'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="36" role="img" aria-label="{escape(message)}"><rect width="720" height="36" rx="7" fill="#26384c"/><rect width="116" height="36" rx="7" fill="#f4b544"/><text x="14" y="23" font-family="sans-serif" font-size="12" fill="#26384c">GERMANY / DE-LU</text><text x="132" y="23" font-family="sans-serif" font-size="12" fill="#fff">{escape(message)}</text></svg>'''
(root/'docs/assets/today.svg').write_text(svg)
p=root/'README.md'
if p.exists():
 content=p.read_text();updated=re.sub(r'<!-- DAILY:START -->.*?<!-- DAILY:END -->',f'<!-- DAILY:START -->\n{message}\n<!-- DAILY:END -->',content,flags=re.S);p.write_text(updated)
print(message)
