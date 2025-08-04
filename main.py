import os
import random
import string
import requests
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from wallets import buy_token_with_all_wallets, sell_token_with_all_wallets, fetch_market_data

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")


def generate_coin():
    name = random.choice([
        "ZuckDoge", "MuskPepe", "TrumpInu", "BananaMoon", "WAGMI420", "SolanaSnail"
    ]) + ''.join(random.choices(string.ascii_uppercase, k=2))
    ticker = ''.join(random.choices(string.ascii_uppercase, k=4))
    return name, ticker


def generate_description(name):
    if not HF_API_TOKEN:
        return f"{name} is the hottest meme coin of the week. Don't miss out! 🚀"

    prompt = f"Write a funny viral description for a memecoin called {name}."
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/mrm8488/t5-base-finetuned-summarize-news",
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt},
            timeout=10
        )
        if response.ok:
            return response.json()[0].get('generated_text', '') or f"{name} is going viral. 🚀"
    except Exception as e:
        print(f"⚠️ HuggingFace Error: {e}")
    return f"{name} is the hottest meme coin of the week. Don't miss out! 🚀"


def generate_image_url(name):
    return f"https://robohash.org/{name}.png"


def post_to_pumpfun(name, ticker, description):
    print(f"📤 Posting {name} ({ticker}) to Pump.fun with description: {description}")
    return f"https://pump.fun/{ticker}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Rugpull Bot!\n"
        "Type /create_coin to launch a memecoin.\n"
        "Type /sell_all <MINT_ADDRESS> to dump it."
    )


async def create_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name, ticker = generate_coin()
    description = generate_description(name)
    image_url = generate_image_url(name)
    pumpfun_url = post_to_pumpfun(name, ticker, description)
    mint_address = f"{ticker}_MINT_PLACEHOLDER"

    await update.message.reply_photo(
        photo=image_url,
        caption=(
            f"🚀 *New Coin Launched!*\n\n"
            f"Name: *{name}*\n"
            f"Ticker: *{ticker}*\n"
            f"Mint: `{mint_address}`\n\n"
            f"{description}\n\n"
            f"🔗 [View on Pump.fun]({pumpfun_url})"
        ),
        parse_mode="Markdown"
    )

    buy_token_with_all_wallets(mint_address)

    market = fetch_market_data(mint_address)
    if market:
        await update.message.reply_text(
            f"📈 Price: ${market['priceUsd']}\n💰 Market Cap: ${market['marketCap']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Could not fetch market data from DexScreener.")


async def sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /sell_all <MINT_ADDRESS>")
        return

    mint_address = context.args[0]
    await update.message.reply_text(f"💸 Selling all tokens for mint: {mint_address}")
    sell_token_with_all_wallets(mint_address)

    market = fetch_market_data(mint_address)
    if market:
        await update.message.reply_text(
            f"📉 Post-Sell Market Cap: ${market['marketCap']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Could not fetch updated market data.")


# ✅ Main entry point — no Updater usage
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set in environment variables.")
        return

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create_coin", create_coin))
    app.add_handler(CommandHandler("sell_all", sell_all))

    print("🤖 Rugpull Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
