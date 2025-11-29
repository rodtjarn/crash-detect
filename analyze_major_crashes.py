#!/usr/bin/env python3
"""
Analyze Major Crash Periods
Shows what indicator values were during known major market crashes
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from trading_alert_system import TradingAlertSystem


def analyze_crash_period(system, start_date, end_date, crash_name):
    """Analyze indicators during a specific crash period"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {crash_name}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'='*70}")

    # Fetch data with extra lookback for indicator calculations
    fetch_start = pd.Timestamp(start_date) - pd.Timedelta(days=120)

    index_data = yf.download(
        '^GSPC',
        start=fetch_start,
        end=end_date,
        progress=False
    )
    vix_data = yf.download(
        '^VIX',
        start=fetch_start,
        end=end_date,
        progress=False
    )

    if len(index_data) < 60:
        print("Insufficient data for this period")
        return

    # Combine data
    data = pd.DataFrame(index=index_data.index)
    data['close'] = index_data['Close'].values
    data['vix'] = vix_data['Close'].values
    data['returns'] = data['close'].pct_change()
    data['put_call_ratio'] = system.calculate_put_call_proxy(data)

    # Find the crash period
    crash_data = data[start_date:end_date]

    if len(crash_data) == 0:
        print("No data found for this period")
        return

    # Get peak and trough
    peak_price = crash_data['close'].max()
    trough_price = crash_data['close'].min()
    peak_date = crash_data['close'].idxmax()
    trough_date = crash_data['close'].idxmin()
    total_drop = (trough_price - peak_price) / peak_price * 100

    print(f"\nMarket Movement:")
    print(f"  Peak: ${peak_price:.2f} on {peak_date.date()}")
    print(f"  Trough: ${trough_price:.2f} on {trough_date.date()}")
    print(f"  Total Drop: {total_drop:.2f}%")
    print(f"  Days: {(trough_date - peak_date).days}")

    # Analyze indicators at key points
    print(f"\nIndicator Values During Crash:")
    print(f"{'Date':<12} {'Price':>10} {'Fractal':>10} "
          f"{'VIX':>8} {'P/C':>8} {'Markov':<12}")
    print("-" * 70)

    # Sample key dates during the crash
    for date in pd.date_range(start_date, end_date, freq='3D'):
        if date not in data.index:
            continue

        # Get window for this date
        idx = data.index.get_loc(date)
        if idx < 90:
            continue

        window_start = idx - 90
        window_data = data.iloc[window_start:idx+1].copy()

        try:
            state = system.calculate_current_state(window_data)
            fractal = state['fractal_dimension']
            fractal_str = f"{fractal:.3f}" if fractal else "N/A"

            print(
                f"{date.date()} "
                f"${state['price']:>9.2f} "
                f"{fractal_str:>10} "
                f"{state['vix']:>8.2f} "
                f"{state['put_call_ratio']:>8.2f} "
                f"{state['markov_state']:<12}"
            )

            # Check if signal would trigger
            signal_type, _ = system.check_signal(state)
            if signal_type:
                print(f"          *** {signal_type} SIGNAL TRIGGERED ***")

        except Exception as e:
            continue

    print()


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          MAJOR CRASH ANALYSIS - Indicator Values                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    system = TradingAlertSystem('config.json')

    # Known major crashes in last 5 years
    crashes = [
        {
            'name': 'COVID-19 Crash (Feb-Mar 2020)',
            'start': '2020-02-15',
            'end': '2020-03-31'
        },
        {
            'name': '2022 Bear Market Start',
            'start': '2022-01-01',
            'end': '2022-06-30'
        },
        {
            'name': 'August 2024 Flash Crash',
            'start': '2024-07-15',
            'end': '2024-08-15'
        },
        {
            'name': 'Recent Volatility (Apr 2025)',
            'start': '2025-04-01',
            'end': '2025-04-15'
        }
    ]

    for crash in crashes:
        try:
            analyze_crash_period(
                system,
                crash['start'],
                crash['end'],
                crash['name']
            )
        except Exception as e:
            print(f"\nError analyzing {crash['name']}: {e}\n")

    print("""
INTERPRETATION:
- Fractal < 1.15 = Severe compression (current threshold)
- Fractal < 0.7 = Extreme compression (original threshold, too strict)
- VIX > 30 = High fear (current threshold)
- VIX > 25 = Moderate fear (original threshold)
- P/C > 1.2 = Panic (current threshold)
- Markov = Crisis = Market in crisis mode (current threshold)
- Markov = Volatile = Market unstable (original threshold, catches more)

RECOMMENDATION:
Use current thresholds (Fractal<1.15, VIX>30, Markov=Crisis) for
SEVERE crash detection (1-3 signals/year, high confidence).

For more frequent signals, consider:
- Fractal < 1.2, VIX > 25, Markov = Volatile
""")


if __name__ == "__main__":
    main()
