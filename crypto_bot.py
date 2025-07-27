import pandas as pd
import time
from datetime import datetime
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_STOP_LOSS_LIMIT, TIME_IN_FORCE_GTC

# Replace these with your Binance Testnet API keys
API_KEY = 'your_testnet_api_key'
API_SECRET = 'your_testnet_api_secret'

# Initialize Binance client for testnet
client = Client(API_KEY, API_SECRET, testnet=True)

# Function to get the precision for a trading pair
def get_symbol_info(symbol):
    try:
        info = client.get_symbol_info(symbol)
        step_size = float(info['filters'][2]['stepSize'])  # Quantity precision
        tick_size = float(info['filters'][0]['tickSize'])  # Price precision
        return step_size, tick_size
    except Exception as e:
        print(f"[{datetime.now()}] Error fetching symbol info: {e}")
        return None, None

# Function to round values to the required precision
def round_to_precision(value, precision):
    return round(value, int(-1 * round(precision).as_integer_ratio()[1]))

# Function to read the latest prediction from the CSV file
def get_latest_prediction(file_path):
    try:
        df = pd.read_csv(file_path)
        latest_pred = df['pred'].iloc[-1]  # Get the last prediction value
        print(f"[{datetime.now()}] Latest prediction: {latest_pred}")
        return latest_pred
    except Exception as e:
        print(f"[{datetime.now()}] Error reading prediction file: {e}")
        return None

# Function to calculate stop-loss and limit prices
def calculate_stop_loss_and_limit(current_price, stop_loss_percent=1, limit_percent=1.5):
    stop_price = current_price * (1 - stop_loss_percent / 100)  # Stop-loss price
    limit_price = current_price * (1 - limit_percent / 100)    # Limit price
    print(f"[{datetime.now()}] Calculated stop price: {stop_price}, limit price: {limit_price}")
    return stop_price, limit_price

# Function to place a market order
def place_market_order(symbol, side, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"[{datetime.now()}] Market order placed: {order}")
        return order
    except Exception as e:
        print(f"[{datetime.now()}] Error placing market order: {e}")
        return None

# Function to set a stop-loss order
def set_stop_loss(symbol, quantity, stop_price, limit_price):
    try:
        stop_loss_order = client.create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_STOP_LOSS_LIMIT,
            quantity=quantity,
            price=round(limit_price, 2),  # Binance requires prices to be rounded
            stopPrice=round(stop_price, 2),
            timeInForce=TIME_IN_FORCE_GTC
        )
        print(f"[{datetime.now()}] Stop-loss order placed: {stop_loss_order}")
        return stop_loss_order
    except Exception as e:
        print(f"[{datetime.now()}] Error placing stop-loss order: {e}")
        return None

# Main function to run the bot hour by hour
def run_trading_bot():
    symbol = "BTCUSDT"  # Trading pair
    prediction_file = "pred.csv"  # Path to your prediction file

    # Get precision for the trading pair
    step_size, tick_size = get_symbol_info(symbol)
    if step_size is None or tick_size is None:
        print(f"[{datetime.now()}] Unable to fetch symbol info. Exiting...")
        return

    # Track the last prediction to avoid duplicate trades
    last_prediction = None

    while True:
        print(f"[{datetime.now()}] Starting new trading cycle...")

        # Step 1: Get the latest prediction
        pred = get_latest_prediction(prediction_file)

        if pred is not None and pred != last_prediction:
            # Update the last prediction
            last_prediction = pred

            # Step 2: Get the current price
            current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
            print(f"[{datetime.now()}] Current price: {current_price}")

            # Step 3: Determine whether to buy or sell
            if pred > current_price:
                # Prediction indicates price will increase -> BUY
                print(f"[{datetime.now()}] Prediction indicates price will increase. Placing BUY order...")
                quantity = round_to_precision(0.001, step_size)  # Example fixed quantity
                stop_price, limit_price = calculate_stop_loss_and_limit(current_price)
                market_order = place_market_order(symbol, SIDE_BUY, quantity)

                if market_order:
                    set_stop_loss(symbol, quantity, stop_price, limit_price)

            elif pred < current_price:
                # Prediction indicates price will decrease -> SELL
                print(f"[{datetime.now()}] Prediction indicates price will decrease. Placing SELL order...")
                quantity = round_to_precision(0.001, step_size)  # Example fixed quantity
                stop_price, limit_price = calculate_stop_loss_and_limit(current_price, stop_loss_percent=1, limit_percent=1.5)
                market_order = place_market_order(symbol, SIDE_SELL, quantity)

                if market_order:
                    set_stop_loss(symbol, quantity, stop_price, limit_price)

        else:
            print(f"[{datetime.now()}] No new prediction or prediction unchanged. Skipping this cycle.")

        # Wait for 1 hour before the next cycle
        print(f"[{datetime.now()}] Waiting for the next hour...")
        time.sleep(3600)  # Sleep for 1 hour (3600 seconds)

# Run the bot
if __name__ == "__main__":
    run_trading_bot()
