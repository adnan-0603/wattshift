"""Daily refresh entrypoint: only replaces snapshot after all processing succeeds."""
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import shutil
from .ingest import ingest
from .export import build


def main():
    now=datetime.now(timezone.utc);root=Path(os.getenv('WATTSHIFT_DATA','data/processed'))
    # Write source inputs under the persistent root, separate from the exported snapshot.
    ingest((now-timedelta(days=90)).date().isoformat(),(now+timedelta(days=2)).date().isoformat(),root/'live','quarterhour')
    ingest((now-timedelta(days=3)).date().isoformat(),(now+timedelta(days=1)).date().isoformat(),root/'current-carbon','quarterhour',True)
    payload=build(live_path=str(root/'live/prices.csv'),out=str(root))
    public=Path('apps/console/public/data')
    if public.exists():shutil.copy2(root/'console.json',public/'console.json')
    print('Refreshed',len(payload['prices']),'intervals; snapshot=',root/'console.json')
if __name__=='__main__':main()
