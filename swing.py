import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Set up logging
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token
TOKEN = "7667842032:AAGNIJswWstYylYhR4LGUW9us_sHsYKzNc4"
application = Application.builder().token(TOKEN).build()

# List of major stocks used for swing trading
swing_stocks = ["TCS.NS", "INFY.NS", "HDFCBANK.NS", "RELIANCE.NS", "ICICIBANK.NS",
                "SBIN.NS", "AXISBANK.NS", "HINDUNILVR.NS", "ITC.NS", "BHARTIARTL.NS"]

# Function to get the best swing trade stocks
async def get_best_swing_stocks():
    best_stocks = []
    for stock in swing_stocks:
        try:
            data = yf.download(stock, period="3mo", interval="1d")
            if data.empty:
                continue
            
            # Calculate Indicators
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            data['ATR'] = data['High'].rolling(14).max() - data['Low'].rolling(14).min()

            # Extract the latest values
            last_row = data.iloc[-1]
            rsi = last_row['RSI']
            atr = last_row['ATR']
            close_price = last_row['Close']

            # Swing trade criteria: RSI between 30-50, SMA_20 > SMA_50
            if 30 < rsi < 50 and last_row['SMA_20'] > last_row['SMA_50']:
                best_stocks.append((stock, close_price, atr, rsi))
        except Exception as e:
            logging.error(f"Error processing {stock}: {e}")

    return best_stocks[:5]  # Return top 5 stocks

# Start command handler
async def start(update: Update, context):
    best_stocks = await get_best_swing_stocks()
    
    if not best_stocks:
        await update.message.reply_text("No strong swing trade opportunities found today.")
        return

    keyboard = [[InlineKeyboardButton(f"{stock} - ₹{price:.2f}", callback_data=stock)]
                for stock, price, _, _ in best_stocks]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📊 *Top Swing Trading Opportunities:*", reply_markup=reply_markup, parse_mode="Markdown")

# Button click handler
async def button(update: Update, context):
    query = update.callback_query
    stock = query.data
    
    data = yf.download(stock, period="3mo", interval="1d")
    last_row = data.iloc[-1]
    
    buy_price = last_row['Close'] * 0.99
    sell_price = last_row['Close'] * 1.02
    estimated_days = round(last_row['ATR'] / (sell_price - buy_price), 1)
    estimated_date = datetime.now() + timedelta(days=estimated_days)
    
    message = (
        f"📊 *{stock} Swing Trade Recommendation:*\n"
        f"💰 *Buy Level:* ₹{buy_price:.2f}\n"
        f"💰 *Sell Level:* ₹{sell_price:.2f}\n"
        f"📅 *Estimated Target Date:* {estimated_date.strftime('%d-%b-%Y')}\n"
        f"📈 *RSI:* {last_row['RSI']:.2f} (Overbought > 70, Oversold < 30)\n"
        f"📊 *ATR (Volatility):* ₹{last_row['ATR']:.2f}\n"
    )

    await query.message.reply_text(message, parse_mode="Markdown")

# Main function
def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == "__main__":
    main()
