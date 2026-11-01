"""Fetch a bounded sample through QUANTAXIS's own TDX connector, without changing market tables."""
import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sitecustomize

def main():
    import pandas as pd
    from QUANTAXIS.QAFetch import QATdx
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', default='000001')
    parser.add_argument('--start', default='2026-10-19')
    parser.add_argument('--end', default='2026-10-30')
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / 'samples' / f'tdx-{args.code}-{args.start}-{args.end}'
    destination.mkdir(parents=True, exist_ok=True)
    receipt = {'source': 'QUANTAXIS.QAFetch.QATdx.QA_fetch_get_stock_day', 'code': args.code,
               'start': args.start, 'end': args.end, 'adjustment': 'unadjusted',
               'attempted_at': datetime.now(timezone.utc).isoformat(), 'status': 'running'}
    (destination/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    try:
        from concurrent.futures import ThreadPoolExecutor
        import datetime as dt
        candidates = list({(item['ip'], item['port']) for item in QATdx.stock_ip_list})
        with ThreadPoolExecutor(max_workers=8) as pool:
            probes = list(pool.map(lambda ep: (QATdx.ping(ep[0], ep[1], 'stock'), ep), candidates))
        good = sorted((delay, endpoint) for delay, endpoint in probes if delay < dt.timedelta(seconds=9))
        if not good:
            raise RuntimeError('No configured TDX stock endpoint answered the protocol check.')
        frame = None
        receipt['attempts'] = []
        for _, endpoint in good[:12]:
            QATdx.best_ip['stock'] = {'ip': endpoint[0], 'port': endpoint[1]}
            frame = QATdx.QA_fetch_get_stock_day(args.code, args.start, args.end, if_fq='00', frequence='day', ip=endpoint[0], port=endpoint[1])
            receipt['attempts'].append({'ip': endpoint[0], 'port': endpoint[1], 'rows': 0 if frame is None else len(frame)})
            if frame is not None and not frame.empty:
                break
        receipt['endpoint'] = QATdx.best_ip['stock']
        if frame is None or frame.empty:
            raise RuntimeError('TDX returned no bars; no alternative data source was substituted.')
        frame.to_csv(destination/'raw.csv', index=False, encoding='utf-8-sig')
        frame.to_json(destination/'raw.json', orient='records', date_format='iso', indent=2)
        required = {'code','date','open','high','low','close','vol','amount','date_stamp'}
        if not required.issubset(frame.columns):
            raise ValueError('Missing source fields: ' + str(required-set(frame.columns)))
        if set(frame.code.astype(str)) != {args.code}:
            raise ValueError('Returned security identity does not match requested code')
        if frame.duplicated(['code','date']).any():
            raise ValueError('Duplicate security/date bars')
        if not ((frame.date >= args.start) & (frame.date <= args.end)).all():
            raise ValueError('Returned bars outside requested window')
        numeric = frame[['open','high','low','close','vol','amount']].apply(pd.to_numeric, errors='raise')
        if numeric.isna().any().any() or (numeric[['open','high','low','close']] <= 0).any().any():
            raise ValueError('Missing or invalid numerical source values')
        if not ((numeric.high >= numeric[['open','close','low']].max(axis=1)) &
                (numeric.low <= numeric[['open','close','high']].min(axis=1)) &
                (numeric.vol >= 0) & (numeric.amount >= 0)).all():
            raise ValueError('Invalid OHLC/volume/amount relationship')
        receipt.update(status='fetched', rows=len(frame), columns=list(frame.columns),
                       first_date=str(frame.date.min()), last_date=str(frame.date.max()),
                       units={'price':'CNY', 'vol':'lots of 100 shares', 'amount':'CNY'},
                       validation='identity/date-window/duplicates/numerical/OHLC passed',
                       trading_calendar_coverage='not independently verified', database_market_writes=0)
        print(frame.to_string(index=False))
    except Exception as exc:
        receipt.update(status='failed', error_type=type(exc).__name__, error=str(exc), database_market_writes=0)
        (destination/'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        traceback.print_exc()
    finally:
        (destination/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    sys.exit(0 if receipt['status']=='fetched' else 2)

if __name__ == '__main__':
    main()
