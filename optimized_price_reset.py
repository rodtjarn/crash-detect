#!/usr/bin/env python3
"""
Optimized Dip-Buying Strategy
- Linear progression: $10K, $20K, $30K, $40K...
- 5% trigger for buy signals (single-day drop OR drawdown from last purchase)
- Price-based reset: Reset to $10K when price recovers 5% above last $10K purchase
- $300K annual cap with smart sizing
- Start with $0 (pure opportunistic buying)
"""

import yfinance as yf
from datetime import datetime, timedelta


def main():
    # Configuration
    initial_capital = 0
    base_buy_amount = 10000
    annual_cap = 300000
    dip_threshold = -0.05  # 5% trigger
    reset_threshold = 1.05  # Reset when price 5% above last $10K purchase
    years = 20

    # Fetch data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365 + 180)

    print("="*100)
    print(f"OPTIMIZED DIP-BUYING STRATEGY ({years} Years)")
    print("="*100)
    print(f"\nStrategy:")
    print(f"  - Linear progression: $10K, $20K, $30K, $40K...")
    print(f"  - Trigger: {abs(dip_threshold)*100:.0f}% drop (single-day OR from last purchase)")
    print(f"  - Reset: When price recovers {(reset_threshold-1)*100:.0f}% above last $10K purchase")
    print(f"  - Annual cap: ${annual_cap:,}")
    print(f"  - Smart sizing: Reduces buy to fit cap (min $10K)\n")

    qqq_data = yf.download('QQQ', start=start_date, end=end_date, progress=False)
    prices = qqq_data['Close'].squeeze()

    print(f"✓ Loaded {len(prices)} days")
    print(f"  Period: {prices.index[0].date()} to {prices.index[-1].date()}\n")

    # Initialize
    qqq_shares = 0
    total_invested = 0
    last_purchase_price = None
    last_10k_price = None  # Price of most recent $10K buy
    buy_sequence = 0
    annual_spending = {}

    buys = []
    resets = []
    skips = []

    # Main loop
    for i in range(1, len(prices)):
        date = prices.index[i]
        current_price = prices.iloc[i]
        prev_price = prices.iloc[i-1]

        # Check for price-based reset
        if last_10k_price is not None and current_price > last_10k_price * reset_threshold:
            if buy_sequence > 0:
                buy_sequence = 0
                resets.append({'date': date, 'price': current_price})

        # Check triggers
        daily_return = (current_price - prev_price) / prev_price
        single_day_drop = daily_return <= dip_threshold

        if last_purchase_price is not None:
            drawdown = (current_price - last_purchase_price) / last_purchase_price
            drawdown_trigger = drawdown <= dip_threshold
        else:
            drawdown_trigger = False

        if single_day_drop or drawdown_trigger:
            year = date.year
            spent = annual_spending.get(year, 0)
            remaining_cap = annual_cap - spent

            # Calculate ideal buy amount based on sequence
            ideal_amount = base_buy_amount * (buy_sequence + 1)

            # Smart sizing: try to fit the largest possible buy
            actual_amount = None

            # Try reducing by $10K increments until it fits
            for test_sequence in range(buy_sequence + 1, 0, -1):
                test_amount = base_buy_amount * test_sequence
                if test_amount <= remaining_cap:
                    actual_amount = test_amount
                    break

            if actual_amount is not None and actual_amount >= base_buy_amount:
                # Execute buy
                shares = actual_amount / current_price
                qqq_shares += shares
                total_invested += actual_amount
                annual_spending[year] = spent + actual_amount
                buy_sequence += 1
                last_purchase_price = current_price

                # Track $10K purchase price for reset
                if actual_amount == base_buy_amount:
                    last_10k_price = current_price

                buys.append({
                    'date': date,
                    'price': current_price,
                    'amount': actual_amount,
                    'sequence': buy_sequence,
                    'year': year
                })
            else:
                # Can't fit even $10K, skip
                skips.append({
                    'date': date,
                    'year': year,
                    'remaining': remaining_cap,
                    'wanted': ideal_amount,
                    'price': current_price
                })

    # Results
    final_value = qqq_shares * prices.iloc[-1]
    total_return = (final_value - total_invested) / total_invested * 100 if total_invested > 0 else 0
    annualized = (pow(final_value / total_invested, 1/years) - 1) * 100 if total_invested > 0 else 0
    roi_per_dollar = final_value / total_invested if total_invested > 0 else 0

    print("="*100)
    print("RESULTS")
    print("="*100)
    print(f"\nTotal Invested:    ${total_invested:,.0f}")
    print(f"Final Value:       ${final_value:,.2f}")
    print(f"Total Return:      +{total_return:.2f}%")
    print(f"Annualized Return: {annualized:.2f}%")
    print(f"Return per $1:     ${roi_per_dollar:.2f}")
    print(f"\nTotal Buys:        {len(buys)}")
    print(f"Resets:            {len(resets)}")
    print(f"Skipped:           {len(skips)}")

    # Yearly breakdown
    print(f"\n{'Year':<6} {'Buys':<6} {'Invested':>14} {'% of Cap':>10} {'Skipped':>8}")
    print("-"*50)

    for year in sorted(set([b['year'] for b in buys])):
        year_buys = [b for b in buys if b['year'] == year]
        year_skips = [s for s in skips if s['year'] == year]
        year_inv = sum(b['amount'] for b in year_buys)
        pct_cap = (year_inv / annual_cap) * 100
        inv_formatted = f"${year_inv:,}"
        print(f"{year:<6} {len(year_buys):<6} {inv_formatted:>14} {pct_cap:>9.1f}% {len(year_skips):>8}")

    # Show all purchases and skips with decline analysis
    print(f"\n{'='*100}")
    print("ALL PURCHASES AND SKIPPED OPPORTUNITIES")
    print("="*100)
    print(f"\n{'Date':<12} {'Type':<10} {'Amount':>12} {'Total Invested':>16} {'Price':>10} {'% Decline':>12}")
    print("-"*75)

    # Merge buys and skips, sorted by date
    all_events = []
    for buy in buys:
        all_events.append({'date': buy['date'], 'type': 'BUY', 'amount': buy['amount'], 'price': buy['price']})
    for skip in skips:
        # Get the price on the skip date
        skip_price = prices.loc[skip['date']]
        all_events.append({'date': skip['date'], 'type': 'SKIP', 'amount': skip['wanted'], 'price': skip_price})

    all_events.sort(key=lambda x: x['date'])

    cumulative_invested = 0
    prev_buy_price = None

    for event in all_events:
        if event['type'] == 'BUY':
            cumulative_invested += event['amount']

        # Calculate % decline from previous purchase
        if prev_buy_price is not None:
            decline = ((event['price'] - prev_buy_price) / prev_buy_price) * 100
            decline_str = f"{decline:+.1f}%"
        else:
            decline_str = "First"

        if event['type'] == 'BUY':
            amount_formatted = f"${event['amount']:,}"
            prev_buy_price = event['price']
        else:
            amount_formatted = f"(${event['amount']:,})"  # Parentheses for skipped

        total_formatted = f"${cumulative_invested:,}"

        print(f"{str(event['date'].date()):<12} {event['type']:<10} {amount_formatted:>12} {total_formatted:>16} ${event['price']:>9.2f} {decline_str:>12}")

        if event['type'] == 'BUY':
            prev_buy_price = event['price']

    # Save results with full table
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'dip_buying_strategy_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write(f"OPTIMIZED DIP-BUYING STRATEGY - {years} YEARS\n\n")
        f.write(f"Configuration:\n")
        f.write(f"  Trigger: {abs(dip_threshold)*100:.0f}%\n")
        f.write(f"  Reset Threshold: {(reset_threshold-1)*100:.0f}%\n")
        f.write(f"  Annual Cap: ${annual_cap:,}\n\n")
        f.write(f"Results:\n")
        f.write(f"  Total Invested: ${total_invested:,.0f}\n")
        f.write(f"  Final Value: ${final_value:,.2f}\n")
        f.write(f"  Annualized: {annualized:.2f}%\n")
        f.write(f"  Return per $1: ${roi_per_dollar:.2f}\n\n")
        f.write(f"  Buys: {len(buys)}, Resets: {len(resets)}, Skipped: {len(skips)}\n\n")

        # Write full table
        f.write("="*100 + "\n")
        f.write("ALL PURCHASES AND SKIPPED OPPORTUNITIES\n")
        f.write("="*100 + "\n\n")
        f.write(f"{'Date':<12} {'Type':<10} {'Amount':>12} {'Total Invested':>16} {'Price':>10} {'% Decline':>12}\n")
        f.write("-"*75 + "\n")

        cumulative = 0
        prev_price = None

        for event in all_events:
            if event['type'] == 'BUY':
                cumulative += event['amount']

            if prev_price is not None:
                decline = ((event['price'] - prev_price) / prev_price) * 100
                decline_str = f"{decline:+.1f}%"
            else:
                decline_str = "First"

            if event['type'] == 'BUY':
                amt_fmt = f"${event['amount']:,}"
                prev_price = event['price']
            else:
                amt_fmt = f"(${event['amount']:,})"

            total_fmt = f"${cumulative:,}"

            f.write(f"{str(event['date'].date()):<12} {event['type']:<10} {amt_fmt:>12} {total_fmt:>16} ${event['price']:>9.2f} {decline_str:>12}\n")

    print(f"\n✓ Full results with complete table saved to {filename}\n")


if __name__ == '__main__':
    main()
