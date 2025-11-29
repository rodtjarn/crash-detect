#!/usr/bin/env python3
"""
Backtest 25-Day Hold Strategy
Tests the exact trading strategy: sell 5% long, buy 3x inverse, hold 25 days
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from trading_alert_system import TradingAlertSystem


class StrategyBacktester:
    """Backtest the 25-day hold strategy"""

    def __init__(self, config_file='config.json'):
        """Initialize backtester"""
        self.system = TradingAlertSystem(config_file)
        self.trades = []

    def fetch_historical_data(self, years=20):
        """Fetch historical data for backtesting"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365 + 180)

        print(f"Fetching {years} years of historical data...")
        print(f"From {start_date.date()} to {end_date.date()}")

        # Fetch S&P 500 data
        index_data = yf.download(
            '^GSPC',
            start=start_date,
            end=end_date,
            progress=False
        )

        # Fetch VIX data
        vix_data = yf.download(
            '^VIX',
            start=start_date,
            end=end_date,
            progress=False
        )

        # Fetch 3x inverse ETF (SPXS) data
        spxs_data = yf.download(
            'SPXS',
            start=start_date,
            end=end_date,
            progress=False
        )

        if len(index_data) < 100:
            raise ValueError(f"Insufficient data: {len(index_data)} days")

        # Combine data
        data = pd.DataFrame(index=index_data.index)
        data['close'] = index_data['Close'].values
        data['vix'] = vix_data['Close'].values
        data['returns'] = data['close'].pct_change()
        data['put_call_ratio'] = self.system.calculate_put_call_proxy(data)

        # Add SPXS data (may not exist for early years)
        if len(spxs_data) > 0:
            spxs_df = pd.DataFrame(index=spxs_data.index)
            spxs_df['spxs_close'] = spxs_data['Close'].values
            data = data.join(spxs_df, how='left')
        else:
            data['spxs_close'] = np.nan

        print(f"✓ Fetched {len(data)} days of data\n")
        return data.dropna(subset=['close', 'vix'])

    def simulate_3x_inverse(self, spy_return):
        """
        Simulate 3x inverse ETF return
        If SPY drops 10%, SPXS gains ~30%
        """
        return -3 * spy_return

    def run_backtest(self, data, lookback_window=90):
        """
        Run backtest with 25-day hold strategy

        Strategy:
        1. On signal: Sell 5% of long stocks
        2. Buy 3x inverse ETF with that capital
        3. Hold for 25 days
        4. Sell inverse and return to long
        """
        print("Running backtest with 25-day hold strategy...")
        print("="*70)

        config = self.system.config['trading']
        position_size = config['position_size'] / 100  # 5% = 0.05
        hold_days = config['hold_days']
        min_data_points = self.system.config['data']['min_data_points']

        trades = []
        start_idx = lookback_window
        last_trade_exit = None

        for i in range(start_idx, len(data)):
            current_date = data.index[i]

            # Skip if we're still in a trade
            if last_trade_exit and current_date <= last_trade_exit:
                continue

            # Get data window for this date
            window_start = i - lookback_window
            window_data = data.iloc[window_start:i+1].copy()

            if len(window_data) < min_data_points:
                continue

            # Calculate indicators for this date
            try:
                state = self.system.calculate_current_state(window_data)
                signal_type, conditions = self.system.check_signal(state)

                if signal_type == 'SHORT':
                    # Signal triggered! Execute trade
                    entry_date = current_date
                    entry_price_spy = state['price']

                    # Find exit date (25 trading days later)
                    future_idx = min(i + hold_days, len(data) - 1)
                    exit_date = data.index[future_idx]
                    actual_hold_days = future_idx - i

                    # Get exit price
                    exit_price_spy = data['close'].iloc[future_idx]

                    # Calculate SPY return (what we would have lost staying long)
                    spy_return = (
                        (exit_price_spy - entry_price_spy) /
                        entry_price_spy
                    )

                    # Calculate 3x inverse ETF return
                    if not pd.isna(data['spxs_close'].iloc[i]):
                        # Use actual SPXS data if available
                        entry_price_spxs = data['spxs_close'].iloc[i]
                        if not pd.isna(data['spxs_close'].iloc[future_idx]):
                            exit_price_spxs = (
                                data['spxs_close'].iloc[future_idx]
                            )
                            spxs_return = (
                                (exit_price_spxs - entry_price_spxs) /
                                entry_price_spxs
                            )
                        else:
                            spxs_return = self.simulate_3x_inverse(spy_return)
                    else:
                        # Simulate 3x inverse for early years
                        spxs_return = self.simulate_3x_inverse(spy_return)

                    # Calculate strategy return
                    # 95% stays in SPY, 5% goes to SPXS
                    long_portion = 0.95 * spy_return
                    short_portion = position_size * spxs_return
                    total_return = long_portion + short_portion

                    trade_info = {
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'hold_days': actual_hold_days,
                        'entry_price': entry_price_spy,
                        'exit_price': exit_price_spy,
                        'spy_return': spy_return * 100,
                        'spxs_return': spxs_return * 100,
                        'total_return': total_return * 100,
                        'fractal': state['fractal_dimension'],
                        'vix': state['vix'],
                        'put_call': state['put_call_ratio'],
                        'markov': state['markov_state']
                    }

                    trades.append(trade_info)
                    last_trade_exit = exit_date

                    # Print trade
                    print(
                        f"Trade #{len(trades)}: "
                        f"{entry_date.date()} -> {exit_date.date()} "
                        f"({actual_hold_days}d) | "
                        f"SPY: {spy_return*100:+.2f}% | "
                        f"SPXS: {spxs_return*100:+.2f}% | "
                        f"Total: {total_return*100:+.2f}%"
                    )

            except Exception as e:
                continue

        self.trades = trades
        return trades

    def analyze_results(self, trades):
        """Analyze backtest results"""
        print("\n" + "="*70)
        print("BACKTEST RESULTS - 25-DAY HOLD STRATEGY")
        print("="*70)

        if not trades:
            print("\n❌ NO TRADES EXECUTED")
            return

        print(f"\n✓ Executed {len(trades)} trades\n")

        # Detailed trade information
        print("TRADE HISTORY:")
        print("-" * 70)
        for i, trade in enumerate(trades, 1):
            print(f"\nTrade #{i}:")
            print(f"  Entry: {trade['entry_date'].date()}")
            print(f"  Exit: {trade['exit_date'].date()}")
            print(f"  Hold: {trade['hold_days']} days")
            print(
                f"  SPY: ${trade['entry_price']:.2f} -> "
                f"${trade['exit_price']:.2f} "
                f"({trade['spy_return']:+.2f}%)"
            )
            print(f"  SPXS Return: {trade['spxs_return']:+.2f}%")
            print(f"  Strategy Return: {trade['total_return']:+.2f}%")

        # Summary statistics
        print("\n" + "="*70)
        print("SUMMARY STATISTICS")
        print("="*70)

        spy_returns = [t['spy_return'] for t in trades]
        spxs_returns = [t['spxs_return'] for t in trades]
        total_returns = [t['total_return'] for t in trades]

        print(f"\nTotal trades: {len(trades)}")
        print(f"\nSTRATEGY PERFORMANCE:")
        print(f"  Average return per trade: {np.mean(total_returns):.2f}%")
        print(f"  Median return: {np.median(total_returns):.2f}%")
        print(f"  Best trade: {np.max(total_returns):.2f}%")
        print(f"  Worst trade: {np.min(total_returns):.2f}%")
        print(
            f"  Win rate: "
            f"{sum(1 for r in total_returns if r > 0) / len(total_returns) * 100:.1f}%"
        )

        print(f"\nCOMPARISON:")
        print(f"  SPY avg (if stayed long): {np.mean(spy_returns):.2f}%")
        print(f"  SPXS avg (5% position): {np.mean(spxs_returns):.2f}%")

        # Calculate cumulative returns
        cumulative_strategy = 1.0
        cumulative_spy = 1.0
        for trade in trades:
            cumulative_strategy *= (1 + trade['total_return'] / 100)
            cumulative_spy *= (1 + trade['spy_return'] / 100)

        print(f"\nCUMULATIVE RETURNS:")
        print(
            f"  Strategy: "
            f"{(cumulative_strategy - 1) * 100:.2f}% total"
        )
        print(
            f"  Buy & Hold SPY: "
            f"{(cumulative_spy - 1) * 100:.2f}% total"
        )
        print(
            f"  Outperformance: "
            f"{((cumulative_strategy - cumulative_spy) / cumulative_spy * 100):.2f}%"
        )

        # Annual statistics
        if len(trades) > 0:
            years = (
                (trades[-1]['exit_date'] - trades[0]['entry_date']).days /
                365.25
            )
            if years > 0:
                trades_per_year = len(trades) / years
                print(f"\nANNUAL METRICS:")
                print(f"  Trades per year: {trades_per_year:.1f}")

        print("\n" + "="*70)


def main():
    """Main entry point"""
    import sys

    years = 20
    if len(sys.argv) > 1:
        try:
            years = int(sys.argv[1])
        except ValueError:
            print("Usage: python backtest_25day_strategy.py [years]")
            sys.exit(1)

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          25-DAY HOLD STRATEGY BACKTEST - {years} YEARS{' ' * (25 - len(str(years)))}║
║                                                                   ║
║  Strategy: Sell 5% long → Buy 3x inverse → Hold 25 days          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Create backtester
    backtester = StrategyBacktester('config.json')

    # Fetch data
    data = backtester.fetch_historical_data(years=years)

    # Run backtest
    trades = backtester.run_backtest(data)

    # Analyze results
    backtester.analyze_results(trades)

    print("\n")


if __name__ == "__main__":
    main()
