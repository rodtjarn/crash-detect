#!/usr/bin/env python3
"""
ML-Driven Buy-and-Hold Strategy
================================
Uses ML crash detection to identify optimal buying opportunities.
Never sells - holds QQQ forever.
Investment amount based on ML confidence and drawdown depth.

Strategy:
- Start with $250k cash
- Buy QQQ when ML model signals opportunity
- Investment amount = f(probability, drawdown, available_cash)
- Hold forever (no selling)
- Track portfolio value over time
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ml_crash_detector import MLCrashDetector
import random
import warnings
warnings.filterwarnings('ignore')


def calculate_investment_amount(probability, drawdown, available_cash,
                                 min_investment=5000, max_pct=0.20):
    """
    Calculate optimal investment amount based on:
    - Model confidence (probability)
    - Drawdown depth (bigger dips = bigger buys)
    - Available cash

    Args:
        probability: ML model probability (0-1)
        drawdown: Current drawdown from ATH (negative value)
        available_cash: Cash available to invest
        min_investment: Minimum investment amount
        max_pct: Maximum % of cash to invest per signal

    Returns:
        Investment amount in dollars
    """

    # Base investment percentage from probability
    # probability >= 0.5 triggers buy, scale from 5% to 20% of cash
    if probability < 0.5:
        return 0

    # Scale investment with probability (0.5 -> 5%, 1.0 -> 20%)
    prob_factor = (probability - 0.5) * 2  # Normalize to 0-1
    base_pct = 0.05 + (prob_factor * 0.15)  # 5% to 20%

    # Increase investment for deeper drawdowns
    # -5% drawdown = 1x, -10% = 1.5x, -20% = 2x, -30% = 2.5x
    drawdown_magnitude = abs(drawdown)
    drawdown_multiplier = 1 + (drawdown_magnitude - 0.05) / 0.10
    drawdown_multiplier = np.clip(drawdown_multiplier, 1.0, 3.0)

    # Calculate investment
    investment_pct = min(base_pct * drawdown_multiplier, max_pct)
    investment = available_cash * investment_pct

    # Ensure minimum investment
    if investment < min_investment and available_cash >= min_investment:
        investment = min_investment

    # Don't invest if insufficient cash
    if available_cash < min_investment:
        investment = 0

    return investment


def backtest_buy_and_hold(
    start_date,
    end_date,
    initial_capital=250000,
    min_investment=5000,
    max_investment_pct=0.20,
    probability_threshold=0.5,
    cooldown_days=5  # Min days between purchases
):
    """
    Backtest buy-and-hold strategy on a specific time period
    """

    # Load trained model
    detector = MLCrashDetector()
    detector.load_model('ml_crash_model.pkl')

    # Fetch QQQ data
    qqq_data = yf.download('QQQ', start=start_date, end=end_date, progress=False)

    data = pd.DataFrame()
    data['close'] = qqq_data['Close']
    data['high'] = qqq_data['High']
    data['low'] = qqq_data['Low']
    data['volume'] = qqq_data['Volume']

    # Fetch VIX
    vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)
    data['vix'] = vix_data['Close']

    data = data.dropna()

    if len(data) < 200:
        return None  # Insufficient data

    # Calculate features
    data = detector.calculate_technical_indicators(data)
    data = data.dropna(subset=detector.feature_names)

    # Initialize portfolio
    cash = initial_capital
    shares = 0
    purchases = []
    last_purchase_date = None

    # Run backtest
    for i in range(len(data)):
        current_date = data.index[i]
        current_price = data['close'].iloc[i]

        # Calculate portfolio value
        portfolio_value = cash + (shares * current_price)

        # Check cooldown
        if last_purchase_date is not None:
            days_since_purchase = (current_date - last_purchase_date).days
            if days_since_purchase < cooldown_days:
                continue

        # Get ML prediction
        features = data.iloc[i][detector.feature_names].values.reshape(1, -1)
        probability = detector.model.predict_proba(features)[0, 1]

        # Check if buy signal
        if probability >= probability_threshold and cash >= min_investment:
            # Calculate investment amount
            drawdown = data.iloc[i]['drawdown']
            investment = calculate_investment_amount(
                probability, drawdown, cash, min_investment, max_investment_pct
            )

            if investment > 0:
                # Execute purchase
                shares_bought = investment / current_price
                shares += shares_bought
                cash -= investment

                purchases.append({
                    'date': current_date,
                    'price': current_price,
                    'shares': shares_bought,
                    'investment': investment,
                    'probability': probability,
                    'drawdown': drawdown,
                    'cash_remaining': cash,
                    'total_shares': shares
                })

                last_purchase_date = current_date

    # Calculate final results
    final_price = data['close'].iloc[-1]
    final_value = cash + (shares * final_price)
    total_invested = initial_capital - cash

    return {
        'start_date': data.index[0],
        'end_date': data.index[-1],
        'initial_capital': initial_capital,
        'final_value': final_value,
        'cash_remaining': cash,
        'total_invested': total_invested,
        'shares_owned': shares,
        'final_price': final_price,
        'total_return': (final_value - initial_capital) / initial_capital,
        'invested_return': (final_value - initial_capital) / total_invested if total_invested > 0 else 0,
        'num_purchases': len(purchases),
        'purchases': purchases
    }


def backtest_random_periods(
    num_periods=10,
    period_years=10,
    initial_capital=250000
):
    """
    Backtest on random time periods
    """

    print(f"{'='*80}")
    print("ML BUY-AND-HOLD STRATEGY - Random Period Backtest")
    print(f"{'='*80}")

    print(f"\nStrategy: Buy QQQ on ML-detected crashes, hold forever")
    print(f"Initial Capital: ${initial_capital:,}")
    print(f"Investment Tool: QQQ")
    print(f"Time Period: Random {period_years}-year windows")
    print(f"Number of Trials: {num_periods}")

    # Fetch full historical data
    print(f"\nFetching historical data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=25 * 365)

    qqq_data = yf.download('QQQ', start=start_date, end=end_date, progress=False)

    print(f"✓ Loaded {len(qqq_data)} days of QQQ data")
    print(f"  Period: {qqq_data.index[0].date()} to {qqq_data.index[-1].date()}")

    # Generate random periods
    print(f"\nRunning {num_periods} random {period_years}-year backtests...")
    print(f"{'='*80}\n")

    results = []

    # Calculate valid date range
    min_start_idx = 200  # Need data for features
    max_start_idx = len(qqq_data) - (period_years * 252)

    if max_start_idx <= min_start_idx:
        print("Error: Insufficient data for requested period length")
        return

    for trial in range(num_periods):
        # Random start index
        start_idx = random.randint(min_start_idx, max_start_idx)
        end_idx = start_idx + (period_years * 252)

        trial_start = qqq_data.index[start_idx]
        trial_end = qqq_data.index[min(end_idx, len(qqq_data)-1)]

        # Run backtest
        result = backtest_buy_and_hold(
            trial_start,
            trial_end,
            initial_capital=initial_capital
        )

        if result is None:
            continue

        # Calculate buy-and-hold comparison (lump sum at start)
        buy_hold_shares = initial_capital / result['purchases'][0]['price'] if result['purchases'] else initial_capital / result['final_price']
        buy_hold_value = buy_hold_shares * result['final_price']
        buy_hold_return = (buy_hold_value - initial_capital) / initial_capital

        # Calculate DCA comparison
        # Invest equally on first Monday of each month
        months_in_period = period_years * 12
        monthly_investment = initial_capital / months_in_period

        # Fetch monthly data for DCA
        dca_data = yf.download('QQQ', start=trial_start, end=trial_end, progress=False)
        dca_shares = 0

        for month_offset in range(months_in_period):
            target_date = trial_start + timedelta(days=30*month_offset)
            # Find closest trading day
            closest_idx = dca_data.index.get_indexer([target_date], method='nearest')[0]
            if closest_idx < len(dca_data):
                price = float(dca_data['Close'].iloc[closest_idx])
                dca_shares += monthly_investment / price

        dca_value = dca_shares * result['final_price']
        dca_return = (dca_value - initial_capital) / initial_capital

        result['buy_hold_return'] = buy_hold_return
        result['buy_hold_value'] = buy_hold_value
        result['dca_return'] = dca_return
        result['dca_value'] = dca_value

        results.append(result)

        # Display
        print(f"Trial #{trial + 1:2d}: {result['start_date'].date()} to {result['end_date'].date()}")
        print(f"  Purchases: {result['num_purchases']}")
        print(f"  Invested: ${result['total_invested']:,.0f} (${result['cash_remaining']:,.0f} cash left)")
        print(f"  Final Value: ${result['final_value']:,.0f}")
        print(f"  ML Strategy Return: {result['total_return']*100:+.2f}%")
        print(f"  Buy & Hold Return:  {buy_hold_return*100:+.2f}%")
        print(f"  DCA Return:         {dca_return*100:+.2f}%")
        print(f"  Outperformance vs Buy&Hold: {(result['total_return'] - buy_hold_return)*100:+.2f}%")
        print()

    # Summary statistics
    if len(results) == 0:
        print("No valid results")
        return

    print(f"{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}\n")

    ml_returns = [r['total_return'] for r in results]
    buy_hold_returns = [r['buy_hold_return'] for r in results]
    dca_returns = [r['dca_return'] for r in results]

    print(f"ML Strategy:")
    print(f"  Average Return:    {np.mean(ml_returns)*100:+.2f}%")
    print(f"  Median Return:     {np.median(ml_returns)*100:+.2f}%")
    print(f"  Min Return:        {np.min(ml_returns)*100:+.2f}%")
    print(f"  Max Return:        {np.max(ml_returns)*100:+.2f}%")
    print(f"  Std Dev:           {np.std(ml_returns)*100:.2f}%")

    print(f"\nBuy & Hold (Lump Sum):")
    print(f"  Average Return:    {np.mean(buy_hold_returns)*100:+.2f}%")
    print(f"  Median Return:     {np.median(buy_hold_returns)*100:+.2f}%")

    print(f"\nDollar Cost Averaging:")
    print(f"  Average Return:    {np.mean(dca_returns)*100:+.2f}%")
    print(f"  Median Return:     {np.median(dca_returns)*100:+.2f}%")

    print(f"\nOutperformance:")
    outperf_buy_hold = [(ml - bh) * 100 for ml, bh in zip(ml_returns, buy_hold_returns)]
    outperf_dca = [(ml - dca) * 100 for ml, dca in zip(ml_returns, dca_returns)]

    print(f"  vs Buy & Hold:     {np.mean(outperf_buy_hold):+.2f}% avg")
    print(f"  vs DCA:            {np.mean(outperf_dca):+.2f}% avg")

    wins_vs_buy_hold = sum(1 for o in outperf_buy_hold if o > 0)
    wins_vs_dca = sum(1 for o in outperf_dca if o > 0)

    print(f"\nWin Rate:")
    print(f"  vs Buy & Hold:     {wins_vs_buy_hold}/{len(results)} ({wins_vs_buy_hold/len(results)*100:.1f}%)")
    print(f"  vs DCA:            {wins_vs_dca}/{len(results)} ({wins_vs_dca/len(results)*100:.1f}%)")

    # Purchase statistics
    avg_purchases = np.mean([r['num_purchases'] for r in results])
    avg_invested = np.mean([r['total_invested'] for r in results])
    avg_cash_left = np.mean([r['cash_remaining'] for r in results])

    print(f"\nInvestment Statistics:")
    print(f"  Avg Purchases:     {avg_purchases:.1f}")
    print(f"  Avg Invested:      ${avg_invested:,.0f}")
    print(f"  Avg Cash Remaining: ${avg_cash_left:,.0f} ({avg_cash_left/initial_capital*100:.1f}%)")

    # Best and worst periods
    best = max(results, key=lambda x: x['total_return'])
    worst = min(results, key=lambda x: x['total_return'])

    print(f"\n{'='*80}")
    print("BEST AND WORST PERIODS")
    print(f"{'='*80}\n")

    print(f"Best Period:")
    print(f"  {best['start_date'].date()} to {best['end_date'].date()}")
    print(f"  ML Return: {best['total_return']*100:+.2f}%")
    print(f"  Buy & Hold: {best['buy_hold_return']*100:+.2f}%")
    print(f"  Purchases: {best['num_purchases']}, Invested: ${best['total_invested']:,.0f}")

    print(f"\nWorst Period:")
    print(f"  {worst['start_date'].date()} to {worst['end_date'].date()}")
    print(f"  ML Return: {worst['total_return']*100:+.2f}%")
    print(f"  Buy & Hold: {worst['buy_hold_return']*100:+.2f}%")
    print(f"  Purchases: {worst['num_purchases']}, Invested: ${worst['total_invested']:,.0f}")

    # Detailed purchase analysis for one period
    print(f"\n{'='*80}")
    print(f"SAMPLE PURCHASE DETAILS (Trial #1)")
    print(f"{'='*80}\n")

    sample = results[0]
    for i, purchase in enumerate(sample['purchases'], 1):
        print(f"Purchase #{i}: {purchase['date'].date()}")
        print(f"  Price: ${purchase['price']:.2f}")
        print(f"  Investment: ${purchase['investment']:,.0f}")
        print(f"  Shares: {purchase['shares']:.2f}")
        print(f"  ML Probability: {purchase['probability']*100:.1f}%")
        print(f"  Drawdown: {purchase['drawdown']*100:.2f}%")
        print(f"  Cash Remaining: ${purchase['cash_remaining']:,.0f}")
        print()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ml_buy_hold_backtest_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write("ML BUY-AND-HOLD STRATEGY BACKTEST\n")
        f.write("="*80 + "\n\n")
        f.write(f"Initial Capital: ${initial_capital:,}\n")
        f.write(f"Period Length: {period_years} years\n")
        f.write(f"Trials: {len(results)}\n\n")

        f.write(f"ML Strategy Average Return: {np.mean(ml_returns)*100:+.2f}%\n")
        f.write(f"Buy & Hold Average Return:  {np.mean(buy_hold_returns)*100:+.2f}%\n")
        f.write(f"DCA Average Return:         {np.mean(dca_returns)*100:+.2f}%\n")
        f.write(f"Outperformance vs Buy&Hold: {np.mean(outperf_buy_hold):+.2f}%\n\n")

        f.write("TRIAL DETAILS:\n")
        f.write("="*80 + "\n\n")

        for i, r in enumerate(results, 1):
            f.write(f"Trial #{i}: {r['start_date'].date()} to {r['end_date'].date()}\n")
            f.write(f"  ML Return: {r['total_return']*100:+.2f}%\n")
            f.write(f"  Buy & Hold: {r['buy_hold_return']*100:+.2f}%\n")
            f.write(f"  DCA: {r['dca_return']*100:+.2f}%\n")
            f.write(f"  Purchases: {r['num_purchases']}\n")
            f.write(f"  Invested: ${r['total_invested']:,.0f}\n\n")

    print(f"✓ Results saved to {filename}\n")


if __name__ == '__main__':
    backtest_random_periods(
        num_periods=15,
        period_years=10,
        initial_capital=250000
    )
