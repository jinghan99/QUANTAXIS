"""Read-only MA signal example. No market data or orders are written."""
import argparse
import json
import sys

import pandas as pd
import QUANTAXIS as QA
from QUANTAXIS.QAUtil import DATABASE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--fast', type=int, default=5)
    parser.add_argument('--slow', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.fast < args.slow:
        parser.error('Require 1 <= fast < slow')
    if args.start > args.end:
        parser.error('start must not be later than end')
    if DATABASE.stock_day.count_documents({'code': args.code}, limit=1) == 0:
        print(json.dumps({'status': 'unavailable', 'reason': 'No persisted stock_day data for this code', 'code': args.code}))
        return 2
    data = QA.QA_fetch_stock_day_adv(args.code, args.start, args.end)
    if data is None or data.data.empty:
        print(json.dumps({'status': 'unavailable', 'reason': 'No data in requested date window'}))
        return 2
    frame = data.data.reset_index().sort_values(['date', 'code']).copy()
    if frame.duplicated(['date', 'code']).any():
        raise ValueError('Duplicate daily bars')
    close = pd.to_numeric(frame['close'], errors='raise')
    if close.isna().any() or (close <= 0).any():
        raise ValueError('Invalid close price')
    if len(frame) < args.slow + 1:
        print(json.dumps({'status': 'unavailable', 'reason': 'Insufficient bars for warmup'}))
        return 2
    frame['ma_fast'] = QA.MA(close, args.fast)
    frame['ma_slow'] = QA.MA(close, args.slow)
    ready = frame.ma_slow.notna()
    frame['signal_at_close'] = (frame.ma_fast > frame.ma_slow).where(ready).astype('Int64')
    frame['signal_for_next_bar'] = frame.signal_at_close.shift(1)
    print(frame[['date', 'code', 'close', 'ma_fast', 'ma_slow', 'signal_at_close', 'signal_for_next_bar']].tail(10).to_string(index=False))
    print('research_signal_only: unadjusted close; no costs, fills, orders, or backtest returns calculated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
