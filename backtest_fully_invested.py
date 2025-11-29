#!/usr/bin/env python3
"""
Fully Invested Portfolio Backtest
$100K always in SPY, sell 3% for SPXS on signals, 30% gain target, reinvest proceeds
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from trading_alert_system import TradingAlertSystem


class FullyInvestedBacktester:
    """Backtest with 100% invested portfolio"""

    def __init__(self, config_file='config.json'):
        """Initialize backtester"""
        self.system = TradingAlertSystem(config_file)
        self.trades = []
        self.portfolio_history = []

    def fetch_historical_data(self, years=20):
        """Fetch historical data for backtesting"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365 + 180)

        print(f"Fetching {years} years of historical data...")
        print(f"From {start_date.date()} to {end_date.date()}")

        # Fetch SPY data
        spy_data = yf.download(
            'SPY',
            start=start_date,
            end=end_date,
            progress=False
        )

        # Fetch S&P 500 index for signals
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
        data['spy'] = spy_data['Close'].values
        data['vix'] = vix_data['Close'].values
        data['returns'] = data['close'].pct_change()
        data['put_call_ratio'] = self.system.calculate_put_call_proxy(data)

        # Add SPXS data
        if len(spxs_data) > 0:
            spxs_df = pd.DataFrame(index=spxs_data.index)
            spxs_df['spxs'] = spxs_data['Close'].values
            data = data.join(spxs_df, how='left')
        else:
            data['spxs'] = np.nan

        print(f"✓ Fetched {len(data)} days of data\n")
        return data.dropna(subset=['close', 'vix', 'spy'])

    def simulate_3x_inverse(self, spy_return):
        """Simulate 3x inverse ETF return"""
        return -3 * spy_return

    def run_backtest(self, data, lookback_window=90):
        """
        Run backtest with fully invested portfolio

        Strategy:
        - Start: $100K fully invested in SPY
        - Signal: Sell 3% of SPY, buy SPXS
        - Exit: SPXS at 30% gain, 5% loss, or 8 days
        - Reinvest: All proceeds back into SPY
        - SPY position grows with market during trade
        """
        print("Running fully invested portfolio backtest...")
        print("="*70)

        config = self.system.config['trading']
        initial_capital = config.get('initial_capital', 100000)
        position_pct = config['position_size'] / 100  # 3% = 0.03
        hold_days = config['hold_days']
        gain_target = config.get('gain_target', 30.0) / 100  # 30% = 0.30
        stop_loss = config.get('stop_loss', 5.0) / 100  # 5% = 0.05
        min_data_points = self.system.config['data']['min_data_points']

        print(f"Initial Capital: ${initial_capital:,.2f}")
        print(f"Position Size: {position_pct*100:.1f}%")
        print(f"Gain Target: {gain_target*100:.1f}%")
        print(f"Stop Loss: {stop_loss*100:.1f}%")
        print(f"Max Hold: {hold_days} days\n")

        # Portfolio starts 100% in SPY
        portfolio_value = initial_capital
        spy_shares = initial_capital / data['spy'].iloc[lookback_window]

        print(f"Initial SPY purchase: {spy_shares:.2f} shares @ "
              f"${data['spy'].iloc[lookback_window]:.2f}\n")

        trades = []
        start_idx = lookback_window
        last_trade_exit_idx = None
        cumulative_gain = 0

        for i in range(start_idx, len(data)):
            current_date = data.index[i]

            # Skip if we're still in a trade
            if last_trade_exit_idx and i <= last_trade_exit_idx:
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
                    # SIGNAL TRIGGERED!
                    entry_date = current_date
                    entry_idx = i

                    # Current portfolio value (all in SPY)
                    current_spy_price = data['spy'].iloc[i]
                    portfolio_value = spy_shares * current_spy_price

                    # Sell 3% of SPY for SPXS
                    spy_to_sell_value = portfolio_value * position_pct
                    spy_shares_to_sell = spy_to_sell_value / current_spy_price
                    spy_shares_remaining = spy_shares - spy_shares_to_sell

                    # Buy SPXS
                    if not pd.isna(data['spxs'].iloc[i]):
                        entry_price_spxs = data['spxs'].iloc[i]
                        use_real_spxs = True
                    else:
                        entry_price_spxs = 100  # Simulated
                        use_real_spxs = False

                    spxs_shares = spy_to_sell_value / entry_price_spxs

                    # Monitor for exit daily
                    exit_date = None
                    exit_idx = None
                    exit_reason = None
                    days_held = 0

                    for j in range(i + 1, min(i + hold_days + 1, len(data))):
                        check_date = data.index[j]
                        days_held = j - i

                        # Get current prices
                        current_spy_price_check = data['spy'].iloc[j]

                        if use_real_spxs and not pd.isna(data['spxs'].iloc[j]):
                            current_spxs = data['spxs'].iloc[j]
                        else:
                            # Simulate SPXS
                            spy_return = (
                                (data['close'].iloc[j] -
                                 data['close'].iloc[i]) /
                                data['close'].iloc[i]
                            )
                            simulated_return = self.simulate_3x_inverse(
                                spy_return
                            )
                            current_spxs = entry_price_spxs * (
                                1 + simulated_return
                            )

                        # Calculate SPXS return
                        spxs_return = (
                            (current_spxs - entry_price_spxs) /
                            entry_price_spxs
                        )

                        # Check exit conditions
                        if spxs_return >= gain_target:
                            exit_date = check_date
                            exit_idx = j
                            exit_spxs_price = current_spxs
                            exit_spy_price = current_spy_price_check
                            exit_reason = (
                                f"GAIN TARGET ({spxs_return*100:.1f}%)"
                            )
                            break
                        elif spxs_return <= -stop_loss:
                            exit_date = check_date
                            exit_idx = j
                            exit_spxs_price = current_spxs
                            exit_spy_price = current_spy_price_check
                            exit_reason = (
                                f"STOP LOSS ({spxs_return*100:.1f}%)"
                            )
                            break
                        elif days_held >= hold_days:
                            exit_date = check_date
                            exit_idx = j
                            exit_spxs_price = current_spxs
                            exit_spy_price = current_spy_price_check
                            exit_reason = f"TIME EXIT ({days_held}d)"
                            break

                    # If no exit found, use last available data
                    if exit_date is None:
                        exit_idx = min(i + hold_days, len(data) - 1)
                        exit_date = data.index[exit_idx]
                        exit_spy_price = data['spy'].iloc[exit_idx]
                        days_held = exit_idx - i

                        if use_real_spxs and not pd.isna(
                            data['spxs'].iloc[exit_idx]
                        ):
                            exit_spxs_price = data['spxs'].iloc[exit_idx]
                        else:
                            spy_return = (
                                (data['close'].iloc[exit_idx] -
                                 data['close'].iloc[i]) /
                                data['close'].iloc[i]
                            )
                            exit_spxs_price = entry_price_spxs * (
                                1 + self.simulate_3x_inverse(spy_return)
                            )
                        exit_reason = f"END OF DATA ({days_held}d)"

                    # Calculate returns
                    spxs_return = (
                        (exit_spxs_price - entry_price_spxs) /
                        entry_price_spxs
                    )

                    # Value of remaining SPY (grew during trade)
                    spy_value_at_exit = (
                        spy_shares_remaining * exit_spy_price
                    )

                    # Value of SPXS position
                    spxs_value_at_exit = spxs_shares * exit_spxs_price

                    # Total portfolio value
                    new_portfolio_value = (
                        spy_value_at_exit + spxs_value_at_exit
                    )

                    # Calculate trade gain/loss
                    trade_gain = new_portfolio_value - portfolio_value
                    trade_return = (
                        (new_portfolio_value - portfolio_value) /
                        portfolio_value * 100
                    )

                    # Update cumulative gain
                    cumulative_gain += trade_gain

                    # Reinvest everything back into SPY
                    spy_shares = new_portfolio_value / exit_spy_price
                    portfolio_value = new_portfolio_value

                    trade_info = {
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'days_held': days_held,
                        'exit_reason': exit_reason,
                        'entry_spy_price': current_spy_price,
                        'exit_spy_price': exit_spy_price,
                        'entry_spxs_price': entry_price_spxs,
                        'exit_spxs_price': exit_spxs_price,
                        'spy_shares_held': spy_shares_remaining,
                        'spxs_shares': spxs_shares,
                        'spxs_return': spxs_return * 100,
                        'portfolio_before': portfolio_value - trade_gain,
                        'portfolio_after': portfolio_value,
                        'trade_gain': trade_gain,
                        'trade_return': trade_return,
                        'cumulative_gain': cumulative_gain,
                        'spy_shares_after': spy_shares,
                        'fractal': state['fractal_dimension'],
                        'vix': state['vix'],
                        'put_call': state['put_call_ratio']
                    }

                    trades.append(trade_info)
                    last_trade_exit_idx = exit_idx

                    # Print trade
                    print(
                        f"Trade #{len(trades)}: "
                        f"{entry_date.date()} -> {exit_date.date()} "
                        f"({days_held}d) | "
                        f"SPXS: {spxs_return*100:+.1f}% | "
                        f"Trade P/L: ${trade_gain:+,.0f} "
                        f"({trade_return:+.2f}%) | "
                        f"Portfolio: ${portfolio_value:,.0f} | "
                        f"Cumulative: ${cumulative_gain:+,.0f} | "
                        f"{exit_reason}"
                    )

            except Exception as e:
                continue

        self.trades = trades

        # Calculate final value (SPY position)
        final_spy_price = data['spy'].iloc[-1]
        final_portfolio_value = spy_shares * final_spy_price

        return trades, final_portfolio_value, cumulative_gain

    def analyze_results(self, trades, final_portfolio, cumulative_gain):
        """Analyze backtest results"""
        print("\n" + "="*70)
        print("FULLY INVESTED PORTFOLIO BACKTEST RESULTS")
        print("="*70)

        config = self.system.config['trading']
        initial_capital = config.get('initial_capital', 100000)

        if not trades:
            print("\n❌ NO TRADES EXECUTED")
            # Calculate buy & hold
            print(f"\nBuy & Hold SPY:")
            print(f"  Final Value: ${final_portfolio:,.2f}")
            total_return = (
                (final_portfolio - initial_capital) / initial_capital * 100
            )
            print(f"  Total Return: {total_return:+.2f}%")
            return

        print(f"\nInitial Capital: ${initial_capital:,.2f}")
        print(f"Final Portfolio: ${final_portfolio:,.2f}")
        print(f"Cumulative Trading Gain: ${cumulative_gain:+,.2f}")
        total_return = (final_portfolio - initial_capital) / initial_capital
        print(f"Total Return: {total_return*100:+.2f}%")
        print(f"\nTotal Trades: {len(trades)}")

        # Exit reason breakdown
        print("\nEXIT REASONS:")
        exit_reasons = {}
        for trade in trades:
            reason = trade['exit_reason'].split('(')[0].strip()
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        for reason, count in sorted(
            exit_reasons.items(), key=lambda x: x[1], reverse=True
        ):
            pct = count / len(trades) * 100
            print(f"  {reason}: {count} ({pct:.1f}%)")

        # Trade statistics
        trade_returns = [t['trade_return'] for t in trades]
        trade_gains = [t['trade_gain'] for t in trades]
        spxs_returns = [t['spxs_return'] for t in trades]

        print(f"\nTRADE PERFORMANCE:")
        print(f"  Average gain per trade: ${np.mean(trade_gains):+,.0f}")
        print(f"  Average return per trade: {np.mean(trade_returns):.2f}%")
        print(f"  Median return: {np.median(trade_returns):.2f}%")
        print(f"  Best trade: ${np.max(trade_gains):+,.0f} "
              f"({np.max(trade_returns):.2f}%)")
        print(f"  Worst trade: ${np.min(trade_gains):+,.0f} "
              f"({np.min(trade_returns):.2f}%)")
        win_rate = (
            sum(1 for g in trade_gains if g > 0) / len(trade_gains)
        )
        print(f"  Win rate: {win_rate*100:.1f}%")

        print(f"\nSPXS POSITION PERFORMANCE:")
        print(f"  Average SPXS return: {np.mean(spxs_returns):.2f}%")
        print(f"  Best SPXS trade: {np.max(spxs_returns):.2f}%")
        print(f"  Worst SPXS trade: {np.min(spxs_returns):.2f}%")

        # Cumulative gain progression
        print(f"\nCUMULATIVE GAIN PROGRESSION:")
        for i in [0, len(trades)//4, len(trades)//2,
                  3*len(trades)//4, len(trades)-1]:
            trade = trades[i]
            print(
                f"  Trade #{i+1} ({trade['entry_date'].date()}): "
                f"${trade['cumulative_gain']:+,.0f}"
            )

        # Annual metrics
        if len(trades) > 0:
            years = (
                (trades[-1]['exit_date'] - trades[0]['entry_date']).days /
                365.25
            )
            if years > 0:
                trades_per_year = len(trades) / years
                annual_return = (
                    (final_portfolio / initial_capital) ** (1/years) - 1
                )
                print(f"\nANNUAL METRICS:")
                print(f"  Trades per year: {trades_per_year:.1f}")
                print(f"  Annualized return: {annual_return*100:.2f}%")

        print("\n" + "="*70)

        return {
            'initial_capital': initial_capital,
            'final_portfolio': final_portfolio,
            'cumulative_gain': cumulative_gain,
            'total_return': total_return * 100,
            'trades': len(trades),
            'win_rate': win_rate * 100,
            'avg_gain': np.mean(trade_gains),
            'best_trade': np.max(trade_gains),
            'worst_trade': np.min(trade_gains)
        }


def main():
    """Main entry point"""
    import sys

    years = 20
    if len(sys.argv) > 1:
        try:
            years = int(sys.argv[1])
        except ValueError:
            print("Usage: python backtest_fully_invested.py [years]")
            sys.exit(1)

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║        FULLY INVESTED PORTFOLIO BACKTEST - {years} YEARS{' ' * (20 - len(str(years)))}║
║                                                                   ║
║  $100K always in SPY                                              ║
║  Signal: Sell 3% SPY → Buy SPXS                                   ║
║  Exit: 30% gain | 5% loss | 8 days                               ║
║  Reinvest: All proceeds back into SPY                             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Create backtester
    backtester = FullyInvestedBacktester('config.json')

    # Fetch data
    data = backtester.fetch_historical_data(years=years)

    # Run backtest
    trades, final_portfolio, cumulative_gain = backtester.run_backtest(data)

    # Analyze results
    summary = backtester.analyze_results(
        trades, final_portfolio, cumulative_gain
    )

    # Save detailed results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'backtest_fully_invested_{timestamp}.txt'

    with open(log_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write(f"FULLY INVESTED PORTFOLIO BACKTEST - {years} YEARS\n")
        f.write(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write("="*70 + "\n\n")

        f.write("STRATEGY:\n")
        f.write("  - $100K always invested in SPY\n")
        f.write("  - On signal: Sell 3% SPY, buy SPXS\n")
        f.write("  - Exit SPXS at: 30% gain, 5% loss, or 8 days\n")
        f.write("  - Reinvest all proceeds back into SPY\n\n")

        f.write("RESULTS:\n")
        f.write(f"  Initial Capital: ${summary['initial_capital']:,.2f}\n")
        f.write(f"  Final Portfolio: ${summary['final_portfolio']:,.2f}\n")
        f.write(
            f"  Cumulative Trading Gain: "
            f"${summary['cumulative_gain']:+,.2f}\n"
        )
        f.write(f"  Total Return: {summary['total_return']:+.2f}%\n")
        f.write(f"  Total Trades: {summary['trades']}\n")
        f.write(f"  Win Rate: {summary['win_rate']:.1f}%\n")
        f.write(f"  Average Gain per Trade: ${summary['avg_gain']:+,.0f}\n")
        f.write(f"  Best Trade: ${summary['best_trade']:+,.0f}\n")
        f.write(f"  Worst Trade: ${summary['worst_trade']:+,.0f}\n\n")

        f.write("="*70 + "\n")
        f.write("DETAILED TRADE LOG\n")
        f.write("="*70 + "\n\n")

        for i, trade in enumerate(trades, 1):
            f.write(f"Trade #{i}:\n")
            f.write(f"  Entry: {trade['entry_date'].date()}\n")
            f.write(f"  Exit: {trade['exit_date'].date()}\n")
            f.write(f"  Days: {trade['days_held']}\n")
            f.write(f"  Exit Reason: {trade['exit_reason']}\n")
            f.write(
                f"  SPXS: ${trade['entry_spxs_price']:.2f} -> "
                f"${trade['exit_spxs_price']:.2f} "
                f"({trade['spxs_return']:+.2f}%)\n"
            )
            f.write(
                f"  Portfolio: ${trade['portfolio_before']:,.0f} -> "
                f"${trade['portfolio_after']:,.0f} "
                f"(${trade['trade_gain']:+,.0f})\n"
            )
            f.write(
                f"  Cumulative Gain: ${trade['cumulative_gain']:+,.0f}\n"
            )
            f.write(
                f"  SPY Shares After: {trade['spy_shares_after']:.2f}\n"
            )
            f.write("\n")

    print(f"\n✓ Detailed results saved to: {log_file}")
    print("\n")


if __name__ == "__main__":
    main()
