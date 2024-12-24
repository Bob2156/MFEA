import discord
from discord.ext import commands
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask, request, jsonify
import threading

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Helper function to fetch SMA and volatility
def fetch_sma_and_volatility():
    try:
        ticker = yf.Ticker("^GSPC")  # S&P 500 Index
        data = ticker.history(period="1y")  # Get 1 year of data

        if data.empty or len(data) < 220:
            raise ValueError("Insufficient data to calculate SMA or volatility.")

        sma_220 = round(data['Close'].rolling(window=220).mean().iloc[-1], 2)
        last_close = round(data['Close'].iloc[-1], 2)

        # Calculate 30-day volatility
        recent_data = data[-30:]
        if len(recent_data) < 30:
            raise ValueError("Insufficient data for volatility calculation.")
        daily_returns = recent_data['Close'].pct_change().dropna()
        volatility = round(daily_returns.std() * (252**0.5) * 100, 2)

        return last_close, sma_220, volatility
    except Exception as e:
        raise ValueError(f"Error fetching SMA and volatility: {e}")

# Helper function to fetch treasury rate
def fetch_treasury_rate():
    try:
        URL = "https://www.cnbc.com/quotes/US3M"
        response = requests.get(URL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rate_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})
            if rate_element:
                rate_text = rate_element.text.strip()
                if rate_text.endswith('%'):
                    return round(float(rate_text[:-1]), 2)
        raise ValueError("Failed to fetch treasury rate.")
    except Exception as e:
        raise ValueError(f"Error fetching treasury rate: {e}")

# Flask setup for webhook
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "The bot webhook is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "type" not in data:
        return jsonify({"error": "Invalid payload."}), 400

    if data["type"] == "check":
        try:
            last_close, sma_220, volatility = fetch_sma_and_volatility()
            treasury_rate = fetch_treasury_rate()

            recommendation = None
            if last_close > sma_220:
                if volatility < 14:
                    recommendation = "Risk ON - 100% UPRO or 3x (100% SPY)"
                elif volatility < 24:
                    recommendation = "Risk MID - 100% SSO or 2x (100% SPY)"
                else:
                    recommendation = (
                        "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                        if treasury_rate and treasury_rate < 4
                        else "Risk OFF - 100% SPY or 1x (100% SPY)"
                    )
            else:
                recommendation = (
                    "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                    if treasury_rate and treasury_rate < 4
                    else "Risk OFF - 100% SPY or 1x (100% SPY)"
                )

            return jsonify({
                "last_close": last_close,
                "sma_220": sma_220,
                "volatility": volatility,
                "treasury_rate": treasury_rate,
                "recommendation": recommendation
            })
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Unexpected error: " + str(e)}), 500

    elif data["type"] == "ping":
        return jsonify({"response": "Bot is ready!"})

    elif data["type"] == "commands":
        return jsonify({
            "commands": {
                "!check": "Fetches market data and provides recommendations.",
                "!commands": "Shows the list of commands.",
                "!links": "Provides a link to testfol.io.",
                "!ping": "Checks if the bot is online and responsive."
            }
        })

    elif data["type"] == "links":
        return jsonify({"link": "Check out [testfol.io](https://testfol.io) for more financial tools!"})

    return jsonify({"error": "Unknown request type."}), 400

@app.route("/healthz", methods=["GET"])
def health_check():
    return "OK", 200

# Discord bot command handlers
@bot.command()
async def check(ctx):
    response = requests.post("http://127.0.0.1:8080/webhook", json={"type": "check"})
    if response.status_code == 200:
        data = response.json()
        if "error" in data:
            await ctx.send(f"Error: {data['error']}")
        else:
            embed = discord.Embed(title="Market Financial Evaluation Assistant (MFEA)", color=discord.Color.blue())
            embed.add_field(name="SPX Last Close", value=f"{data['last_close']}", inline=False)
            embed.add_field(name="SMA 220", value=f"{data['sma_220']}", inline=False)
            embed.add_field(name="Volatility (Annualized)", value=f"{data['volatility']}%", inline=False)
            embed.add_field(name="3M Treasury Rate", value=f"{data['treasury_rate']}%", inline=False)
            embed.add_field(name="MFEA Recommendation", value=data['recommendation'], inline=False)
            await ctx.send(embed=embed)
    else:
        await ctx.send("Error: Unable to fetch data.")

@bot.command()
async def ping(ctx):
    response = requests.post("http://127.0.0.1:8080/webhook", json={"type": "ping"})
    if response.status_code == 200:
        data = response.json()
        await ctx.send(data.get("response", "No response from server."))
    else:
        await ctx.send("Error: Unable to reach the server.")

@bot.command()
async def commands(ctx):
    response = requests.post("http://127.0.0.1:8080/webhook", json={"type": "commands"})
    if response.status_code == 200:
        data = response.json()
        commands_list = data.get("commands", {})
        embed = discord.Embed(title="MFEA Bot Commands", color=discord.Color.green())
        for command, description in commands_list.items():
            embed.add_field(name=command, value=description, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Error: Unable to fetch commands.")

@bot.command()
async def links(ctx):
    response = requests.post("http://127.0.0.1:8080/webhook", json={"type": "links"})
    if response.status_code == 200:
        data = response.json()
        await ctx.send(data.get("link", "No link available."))
    else:
        await ctx.send("Error: Unable to fetch link.")

# Run Flask server in a separate thread
def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if PORT is not set
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Ensure Flask thread exits with the main program
    flask_thread.start()

    # Start Discord bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
