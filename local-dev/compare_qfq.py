"""Compare QUANTAXIS's real adjustment function with the Tencent QFQ reply."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sitecustomize
import pandas as pd
import requests
from QUANTAXIS.QAFetch import QATdx
from QUANTAXIS.QAData.data_fq import _QA_data_stock_to_fq


def main():
    root = Path(__file__).resolve().parents[1] / 'samples/qfq-comparison-000001'
    root.mkdir(parents=True, exist_ok=True)
    start, end = '2025-01-01', '2026-10-30'
    endpoint = {'ip':'shtdx.gtjas.com','port':7709}
    raw = QATdx.QA_fetch_get_stock_day('000001', start, end, if_fq='00', **endpoint)
    xdxr = QATdx.QA_fetch_get_stock_xdxr('000001', **endpoint)
    if raw is None or raw.empty or xdxr is None or xdxr.empty:
        raise RuntimeError('Real raw bars and dividend events are both required for this comparison')
    raw.to_csv(root/'tdx-raw.csv', index=False, encoding='utf-8-sig')
    xdxr.to_csv(root/'tdx-xdxr.csv', index=False, encoding='utf-8-sig')
    raw = raw.assign(date=pd.to_datetime(raw.date)).set_index(['date','code'])
    xdxr = xdxr.assign(date=pd.to_datetime(xdxr.date)).set_index(['date','code'])
    adjusted = _QA_data_stock_to_fq(raw.copy(), xdxr.copy(), 'qfq').reset_index()
    adjusted['date'] = adjusted.date.dt.strftime('%Y-%m-%d')
    adjusted.to_csv(root/'quantaxis-qfq.csv', index=False, encoding='utf-8-sig')
    response = requests.get('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',
        params={'param':f'sz000001,day,{start},{end},640,qfq'}, timeout=20)
    response.raise_for_status()
    (root/'tencent-response.json').write_text(response.text, encoding='utf-8')
    payload = response.json()
    if payload.get('code') != 0:
        raise ValueError('Tencent returned a business error')
    rows = payload['data']['sz000001'].get('qfqday')
    if not rows:
        raise ValueError('Tencent did not return qfqday')
    tencent = pd.DataFrame([row[:6] for row in rows], columns=['date','open','close','high','low','vol'])
    tencent = tencent[(tencent.date >= start) & (tencent.date <= end)].copy()
    for name in ['open','close','high','low','vol']:
        tencent[name] = pd.to_numeric(tencent[name], errors='raise')
    tencent.to_csv(root/'tencent-qfq.csv', index=False, encoding='utf-8-sig')
    joined = adjusted.merge(tencent, on='date', suffixes=('_qa','_tencent'), validate='one_to_one')
    for name in ['open','close','high','low']:
        joined[name+'_delta'] = joined[name+'_qa'] - joined[name+'_tencent']
    differences = joined[[name+'_delta' for name in ['open','close','high','low']]].abs().max(axis=1)
    joined['max_ohlc_delta'] = differences
    joined.to_csv(root/'comparison.csv', index=False, encoding='utf-8-sig')
    events = xdxr.reset_index()
    events = events[(events.category == 1) & (events.date >= pd.Timestamp(start)) & (events.date <= pd.Timestamp(end))]
    summary = {'security':'000001.SZ','start':start,'end':end,'tdx_endpoint':endpoint,
        'quantaxis_rows':len(adjusted),'tencent_rows':len(tencent),'matched_rows':len(joined),
        'dividend_events':events[['date','fenhong','peigu','peigujia','songzhuangu']].astype(str).to_dict('records'),
        'anchor':'2026-10-30 (last TDX bar in this computation)',
        'max_ohlc_abs_difference':float(differences.max()),
        'rows_with_difference_over_0_001':int((differences > 0.001).sum()),
        'all_dates_match':set(adjusted.date)==set(tencent.date),
        'examples':joined[['date','close_qa','close_tencent','close_delta']].iloc[[0,len(joined)//2,-1]].to_dict('records'),
        'database_market_writes':0}
    (root/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
