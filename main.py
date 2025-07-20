import pandas as pd
import yfinance as yf
from datetime import datetime as dt
from zoneinfo import ZoneInfo

# DEFAULT VARS
FILEPATH = 'tickers.csv'
NUM_ATM_STRIKES = 7

# Get tickers I am interested in
df = pd.read_csv(FILEPATH)

for row in df.itertuples(index=True):
    ticker_symbol = row.ticker
    price_target1 = row.pt1
    price_target2 = row.pt2
    price_target3 = row.pt3
    price_target4 = row.pt4
    
    # Fetch the ticker data using yfinance
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    if not info:
        print(f"Ticker {ticker_symbol} not found or no data available.")
        continue
    
    current_price = info.get("regularMarketPrice")
    data = ticker.history(period="1d")

    # Get available option expiration dates
    option_expiries = ticker.options

    if not option_expiries:
        print(f"No options available for ticker {ticker_symbol}.")
        continue
    
    # Fetch option chain for all expiry dates
    for expiry in option_expiries:    
        option_chain = ticker.option_chain(expiry)
        calls = option_chain.calls.sort_values('strike')

        # Calculate absolute distance from current price
        calls['distance'] = (calls['strike'] - current_price).abs()

        # Find the index of the closest strike
        closest_strike_idx = calls['distance'].idxmin()

        # Create a new column 'atm' with '' for all rows
        calls['atm'] = ''

        # Mark the closest strike row with 'X'
        calls.loc[closest_strike_idx, 'atm'] = 'X'

        # Get indices for closest strikes (handle edges)
        start_idx = max(closest_strike_idx - NUM_ATM_STRIKES, 0)
        end_idx = min(closest_strike_idx + NUM_ATM_STRIKES + 1, len(calls))

        # Slice the calls DataFrame for those strikes
        atm_calls = calls.iloc[start_idx:end_idx]
        atm_calls['mid'] = (atm_calls['bid'] + atm_calls['ask']) / 2

        # Calculate the return for each call option given the price targets
        atm_calls['ret_pt1'] = (((price_target1 - atm_calls['strike']).clip(lower=0) - atm_calls['mid']) / atm_calls['mid']).round(2)
        atm_calls['ret_pt2'] = (((price_target2 - atm_calls['strike']).clip(lower=0) - atm_calls['mid']) / atm_calls['mid']).round(2)
        atm_calls['ret_pt3'] = (((price_target3 - atm_calls['strike']).clip(lower=0) - atm_calls['mid']) / atm_calls['mid']).round(2)
        atm_calls['ret_pt4'] = (((price_target4 - atm_calls['strike']).clip(lower=0) - atm_calls['mid']) / atm_calls['mid']).round(2)

        # Print datetime this was captured
        pacific_now = dt.now(ZoneInfo("America/Los_Angeles"))
        atm_calls['pulled_at'] = pacific_now.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"ATM call options for {ticker_symbol} on {expiry} (around strike {current_price}):")
        print(atm_calls[['pulled_at', 'atm', 'strike', 'bid', 'mid', 'ask', 'openInterest', 'volume', 'ret_pt1', 'ret_pt2', 'ret_pt3', 'ret_pt4']])
        
        # puts = option_chain.puts
        print("test")

#TODO: SORT THRU THIS LOGIC

# Example: Add a column for predicted price and calculate potential profit/loss
# Let's say you have a dictionary of predicted prices for each ticker
predicted_prices = {'CLSK': 110, 'AAPL': 160, 'MSFT': 260}

# Add predicted price column
df['predicted_price'] = df['ticker'].map(predicted_prices)

# Calculate intrinsic value for call options (CE) and put options (PE)
def intrinsic_value(row):
    if row['option-type'] == 'CE':
        return max(0, row['predicted_price'] - row['strike-price'])
    else:  # PE
        return max(0, row['strike-price'] - row['predicted_price'])

df['intrinsic_value'] = df.apply(intrinsic_value, axis=1)

# Calculate profit/loss per contract (assuming 1 contract = 1 share for simplicity)
df['profit_loss'] = df['intrinsic_value'] - df['premium']

print(df)
