#!/usr/bin/env python3
"""
Backtest Crash Detection Strategy on Random Time Windows
Tests the current strategy: Fractal < 1.2, P/C > 1.1, VIX > 25
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json


def calculate_fractal_dimension(prices, max_lag=20):
    """
    Calculate fractal dimension using Hurst exponent (R/S analysis)
    Same method as trading_alert_system.py
    """
    if len(prices) < max_lag * 2:
        return None

    lags = range(2, max_lag)
    tau = []

    for lag in lags:
        pp = np.log(prices)
        n = len(pp) // lag
        if n < 2:
            continue

        subseries = [pp[i*lag:(i+1)*lag] for i in range(n)]
        rs_values = []

        for sub in subseries:
            if len(sub) < 2:
                continue

            mean_adj = sub - np.mean(sub)
            cumdev = np.cumsum(mean_adj)
            R = np.max(cumdev) - np.min(cumdev)
            S = np.std(sub)

            if S > 0:
                rs_values.append(R / S)

        if rs_values:
            tau.append(np.mean(rs_values))

    if len(tau) < 2:
        return None

    lags_log = np.log(list(lags[:len(tau)]))
    tau_log = np.log(tau)

    valid = np.isfinite(lags_log) & np.isfinite(tau_log)
    if np.sum(valid) < 2:
        return None

    hurst = np.polyfit(lags_log[valid], tau_log[valid], 1)[0]
    fractal_dim = 2 - hurst

    return fractal_dim


def calculate_put_call_proxy(vix, returns):
    """
    Calculate Put/Call ratio proxy
    Same method as trading_alert_system.py
    """
    vix_normalized = vix / 20
    price_momentum = -returns.rolling(5).mean() * 10
    pc_proxy = 0.8 + (vix_normalized - 1) * 0.3 + price_momentum
    return pc_proxy.clip(0.3, 2.5)


def check_signal(fractal, put_call, vix, thresholds):
    """Check if signal conditions are met"""
    if fractal is None:
        return False

    conditions = {
        'fractal': fractal < thresholds['fractal_max'],
        'put_call': put_call > thresholds['put_call_min'],
        'vix': vix > thresholds['vix_min']
    }

    return all(conditions.values()), conditions


def backtest_period(data, thresholds, lookback_days=90):
    """
    Backtest strategy on a period of data
    Returns list of signals with performance metrics
    """
    signals = []

    # Need at least lookback_days for indicator calculation
    for i in range(lookback_days, len(data)):
        current_date = data.index[i]

        # Get historical window for indicators
        window_data = data.iloc[i-lookback_days:i+1]

        # Calculate indicators using last 60 days of prices
        recent_prices = window_data['close'].values[-60:]
        fractal = calculate_fractal_dimension(recent_prices)

        current_vix = window_data['vix'].iloc[-1]
        current_pc = window_data['put_call_ratio'].iloc[-1]

        # Check if signal triggered
        signal_triggered, conditions = check_signal(fractal, current_pc, current_vix, thresholds)

        if signal_triggered:
            current_price = window_data['close'].iloc[-1]

            # Look forward to measure returns
            returns_forward = {}
            for days in [1, 3, 5, 10, 20]:
                if i + days < len(data):
                    future_price = data['close'].iloc[i + days]
                    ret = (future_price - current_price) / current_price * 100
                    returns_forward[f'ret_{days}d'] = ret
                else:
                    returns_forward[f'ret_{days}d'] = None

            signals.append({
                'date': current_date,
                'price': current_price,
                'fractal': fractal,
                'put_call': current_pc,
                'vix': current_vix,
                **returns_forward
            })

            # Skip next 5 days to avoid duplicate signals
            i += 5

    return signals


def run_backtest_on_random_windows(num_windows=10, window_years=5):
    """
    Run backtest on random time windows
    """
    print("="*80)
    print("CRASH DETECTION STRATEGY BACKTEST - Random Time Windows")
    print("="*80)

    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)

    thresholds = config['trading']['thresholds']

    print(f"\nStrategy Configuration:")
    print(f"  Fractal < {thresholds['fractal_max']}")
    print(f"  Put/Call > {thresholds['put_call_min']}")
    print(f"  VIX > {thresholds['vix_min']}")
    print(f"  Markov: {'Enabled' if thresholds.get('use_markov', False) else 'Disabled'}")

    # Fetch full historical data
    print(f"\nFetching {window_years*2} years of historical data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=window_years * 2 * 365)

    # Fetch S&P 500 data
    index_data = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
    vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)

    # Combine data
    data = pd.DataFrame()
    data['close'] = index_data['Close']
    data['vix'] = vix_data['Close']
    data = data.dropna()

    # Calculate returns and put/call proxy
    data['returns'] = data['close'].pct_change()
    data['put_call_ratio'] = calculate_put_call_proxy(data['vix'], data['returns'])
    data = data.dropna()

    print(f"✓ Loaded {len(data)} days of data")
    print(f"  Period: {data.index[0].date()} to {data.index[-1].date()}")

    # Generate random windows
    print(f"\nRunning {num_windows} random {window_years}-year backtests...\n")
    print("="*80)

    all_signals = []
    window_results = []

    min_idx = 90  # Need lookback
    max_idx = len(data) - (window_years * 252)  # Leave room for window

    if max_idx <= min_idx:
        print("Error: Not enough data for requested window size")
        return

    for trial in range(num_windows):
        # Random window
        start_idx = random.randint(min_idx, max_idx)
        end_idx = start_idx + (window_years * 252)

        window_data = data.iloc[start_idx:end_idx]
        start_date = window_data.index[0]
        end_date = window_data.index[-1]

        # Run backtest on this window
        signals = backtest_period(window_data, thresholds)

        # Calculate statistics for this window
        if len(signals) > 0:
            avg_1d = np.mean([s['ret_1d'] for s in signals if s['ret_1d'] is not None])
            avg_5d = np.mean([s['ret_5d'] for s in signals if s['ret_5d'] is not None])
            avg_20d = np.mean([s['ret_20d'] for s in signals if s['ret_20d'] is not None])

            # Count negative returns (market drops)
            drops_5d = sum(1 for s in signals if s['ret_5d'] is not None and s['ret_5d'] < 0)
            drops_20d = sum(1 for s in signals if s['ret_20d'] is not None and s['ret_20d'] < 0)
        else:
            avg_1d = avg_5d = avg_20d = 0
            drops_5d = drops_20d = 0

        window_results.append({
            'trial': trial + 1,
            'start_date': start_date,
            'end_date': end_date,
            'num_signals': len(signals),
            'avg_1d_return': avg_1d,
            'avg_5d_return': avg_5d,
            'avg_20d_return': avg_20d,
            'drops_5d': drops_5d,
            'drops_20d': drops_20d
        })

        all_signals.extend(signals)

        print(f"Window #{trial + 1:2d}: {start_date.date()} to {end_date.date()}")
        print(f"  Signals: {len(signals)}")
        if len(signals) > 0:
            print(f"  Avg returns: 1d={avg_1d:+.2f}%, 5d={avg_5d:+.2f}%, 20d={avg_20d:+.2f}%")
            print(f"  Market drops: 5d={drops_5d}/{len(signals)}, 20d={drops_20d}/{len(signals)}")
        print()

    # Overall statistics
    print("="*80)
    print("OVERALL RESULTS")
    print("="*80)

    total_signals = len(all_signals)
    print(f"\nTotal signals across all windows: {total_signals}")

    if total_signals > 0:
        # Average returns
        print(f"\nAverage Market Returns After Signal:")
        for days in [1, 3, 5, 10, 20]:
            key = f'ret_{days}d'
            returns = [s[key] for s in all_signals if s[key] is not None]
            if returns:
                avg = np.mean(returns)
                min_ret = np.min(returns)
                max_ret = np.max(returns)
                print(f"  {days:2d} days: {avg:+6.2f}% (min: {min_ret:+6.2f}%, max: {max_ret:+6.2f}%)")

        # Crash detection accuracy
        print(f"\nCrash Detection Accuracy (market drops):")
        for days in [5, 20]:
            key = f'ret_{days}d'
            returns = [s[key] for s in all_signals if s[key] is not None]
            if returns:
                drops = sum(1 for r in returns if r < 0)
                accuracy = drops / len(returns) * 100
                print(f"  {days:2d} days: {drops}/{len(returns)} signals ({accuracy:.1f}%)")

        # 3x inverse ETF returns (assuming SPXS)
        print(f"\n3x Inverse ETF Returns (SPXS equivalent):")
        for days in [5, 20]:
            key = f'ret_{days}d'
            returns = [s[key] for s in all_signals if s[key] is not None]
            if returns:
                inverse_returns = [-r * 3 for r in returns]  # 3x inverse
                avg_inverse = np.mean(inverse_returns)
                min_inverse = np.min(inverse_returns)
                max_inverse = np.max(inverse_returns)
                wins = sum(1 for r in inverse_returns if r > 0)
                win_rate = wins / len(inverse_returns) * 100
                print(f"  {days:2d} days: {avg_inverse:+6.2f}% avg (min: {min_inverse:+6.2f}%, max: {max_inverse:+6.2f}%, win rate: {win_rate:.1f}%)")

        # Best and worst signals
        print(f"\n" + "="*80)
        print("BEST AND WORST SIGNALS")
        print("="*80)

        signals_with_20d = [s for s in all_signals if s['ret_20d'] is not None]
        if signals_with_20d:
            best = min(signals_with_20d, key=lambda x: x['ret_20d'])  # Most negative = best for short
            worst = max(signals_with_20d, key=lambda x: x['ret_20d'])  # Most positive = worst for short

            print(f"\nBest Signal (biggest drop):")
            print(f"  Date: {best['date'].date()}")
            print(f"  Price: ${best['price']:.2f}")
            print(f"  Indicators: Fractal={best['fractal']:.3f}, P/C={best['put_call']:.2f}, VIX={best['vix']:.1f}")
            print(f"  Returns: 1d={best['ret_1d']:+.2f}%, 5d={best['ret_5d']:+.2f}%, 20d={best['ret_20d']:+.2f}%")
            print(f"  3x Inverse: {-best['ret_20d']*3:+.2f}% (20 days)")

            print(f"\nWorst Signal (market went up):")
            print(f"  Date: {worst['date'].date()}")
            print(f"  Price: ${worst['price']:.2f}")
            print(f"  Indicators: Fractal={worst['fractal']:.3f}, P/C={worst['put_call']:.2f}, VIX={worst['vix']:.1f}")
            print(f"  Returns: 1d={worst['ret_1d']:+.2f}%, 5d={worst['ret_5d']:+.2f}%, 20d={worst['ret_20d']:+.2f}%")
            print(f"  3x Inverse: {-worst['ret_20d']*3:+.2f}% (20 days)")

        # Signal frequency
        avg_signals_per_window = np.mean([w['num_signals'] for w in window_results])
        signals_per_year = avg_signals_per_window / window_years

        print(f"\n" + "="*80)
        print("SIGNAL FREQUENCY")
        print("="*80)
        print(f"\nAverage signals per {window_years}-year window: {avg_signals_per_window:.1f}")
        print(f"Estimated signals per year: {signals_per_year:.1f}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'crash_strategy_backtest_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write("CRASH DETECTION STRATEGY BACKTEST\n")
        f.write("="*80 + "\n\n")
        f.write(f"Strategy: Fractal < {thresholds['fractal_max']}, ")
        f.write(f"P/C > {thresholds['put_call_min']}, VIX > {thresholds['vix_min']}\n")
        f.write(f"Windows tested: {num_windows}\n")
        f.write(f"Window size: {window_years} years\n\n")

        f.write(f"TOTAL SIGNALS: {total_signals}\n\n")

        if total_signals > 0:
            f.write("AVERAGE RETURNS AFTER SIGNAL:\n")
            for days in [1, 3, 5, 10, 20]:
                key = f'ret_{days}d'
                returns = [s[key] for s in all_signals if s[key] is not None]
                if returns:
                    avg = np.mean(returns)
                    f.write(f"  {days:2d} days: {avg:+6.2f}%\n")

            f.write("\n3x INVERSE ETF RETURNS:\n")
            for days in [5, 20]:
                key = f'ret_{days}d'
                returns = [s[key] for s in all_signals if s[key] is not None]
                if returns:
                    inverse_returns = [-r * 3 for r in returns]
                    avg_inverse = np.mean(inverse_returns)
                    wins = sum(1 for r in inverse_returns if r > 0)
                    win_rate = wins / len(inverse_returns) * 100
                    f.write(f"  {days:2d} days: {avg_inverse:+6.2f}% avg, {win_rate:.1f}% win rate\n")

            f.write("\nSIGNAL FREQUENCY:\n")
            f.write(f"  Avg signals per window: {avg_signals_per_window:.1f}\n")
            f.write(f"  Estimated per year: {signals_per_year:.1f}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("DETAILED SIGNALS:\n")
            f.write("="*80 + "\n\n")

            for i, sig in enumerate(all_signals, 1):
                f.write(f"Signal #{i}: {sig['date'].date()}\n")
                f.write(f"  Price: ${sig['price']:.2f}\n")
                f.write(f"  Fractal: {sig['fractal']:.3f}, P/C: {sig['put_call']:.2f}, VIX: {sig['vix']:.1f}\n")
                f.write(f"  Returns: 1d={sig['ret_1d']:+.2f}%, 5d={sig['ret_5d']:+.2f}%, 20d={sig['ret_20d']:+.2f}%\n")
                if sig['ret_20d'] is not None:
                    f.write(f"  3x Inverse (20d): {-sig['ret_20d']*3:+.2f}%\n")
                f.write("\n")

    print(f"\n✓ Detailed results saved to {filename}\n")


if __name__ == '__main__':
    run_backtest_on_random_windows(num_windows=15, window_years=5)
