import discord
from discord.ext import commands
from discord import ButtonStyle
from discord.ui import View, Button
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
import threading

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Function to fetch SMA and volatility
def fetch_sma_and_volatility():
    ticker = yf.Ticker("^GSPC")  # S&P 500 Index
    data = ticker.history(period="1y")  # Get 1 year of data
    if data.empty:
        raise ValueError("No data fetched for SPX. This might be due to API issues or incorrect ticker symbol.")
    if len(data) < 220:
        raise ValueError("Not enough data to calculate 220-day SMA. Ensure at least 220 days of historical data is available.")
    
    sma_220 = round(data['Close'].rolling(window=220).mean().iloc[-1], 2)
    last_close = round(data['Close'].iloc[-1], 2)
    
    # Calculate 30-day volatility
    recent_data = data[-30:]  # Last month
    if len(recent_data) < 30:
        raise ValueError("Not enough data to calculate 30-day volatility. Ensure sufficient recent data.")
    daily_returns = recent_data['Close'].pct_change().dropna()
    volatility = round(daily_returns.std() * (252**0.5) * 100, 2)
    
    return last_close, sma_220, volatility

# Function to fetch treasury rate
def fetch_treasury_rate():
    URL = "https://www.cnbc.com/quotes/US3M"  # Example source for 3-month treasury rates
    response = requests.get(URL)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        rate_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})
        if rate_element:
            rate_text = rate_element.text.strip()
            if rate_text.endswith('%'):
                rate_text = rate_text[:-1]  # Remove the '%' symbol
            return round(float(rate_text), 2)
    raise ValueError("Failed to fetch treasury rate. Verify the source URL or HTML structure.")

@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        # Show an interactive menu when the bot is mentioned
        view = View()

        view.add_item(Button(label="Check Market Data", style=ButtonStyle.primary, custom_id="check"))
        view.add_item(Button(label="Commands List", style=ButtonStyle.secondary, custom_id="commands"))
        view.add_item(Button(label="Links", style=ButtonStyle.link, url="https://testfol.io"))
        view.add_item(Button(label="Ping", style=ButtonStyle.success, custom_id="ping"))

        embed = discord.Embed(
            title="Market Financial Evaluation Assistant (MFEA)",
            description="Choose an option below:",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed, view=view)

        async def button_callback(interaction):
            if interaction.custom_id == "check":
                await run_check(interaction)
            elif interaction.custom_id == "commands":
                await show_commands(interaction)
            elif interaction.custom_id == "ping":
                await interaction.response.send_message("Bot is ready!", ephemeral=True)

        # Assign callback to buttons
        for button in view.children:
            if isinstance(button, Button):
                button.callback = button_callback
    await bot.process_commands(message)

# Function to execute !check command
async def run_check(interaction):
    await interaction.response.defer()
    try:
        last_close, sma_220, volatility = fetch_sma_and_volatility()
        treasury_rate = fetch_treasury_rate()

        embed = discord.Embed(title="Market Financial Evaluation Assistant (MFEA)", color=discord.Color.blue())
        embed.add_field(name="SPX Last Close", value=f"{last_close}", inline=False)
        embed.add_field(name="SMA 220", value=f"{sma_220}", inline=False)
        embed.add_field(name="Volatility (Annualized)", value=f"{volatility}%", inline=False)
        embed.add_field(name="3M Treasury Rate", value=f"{treasury_rate}%", inline=False)

        # Recommendation logic
        if last_close > sma_220:
            if volatility < 14:
                recommendation = "Risk ON - 100% UPRO or 3x (100% SPY)"
            elif volatility < 24:
                recommendation = "Risk MID - 100% SSO or 2x (100% SPY)"
            else:
                if treasury_rate and treasury_rate < 4:
                    recommendation = "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
                else:
                    recommendation = "Risk OFF - 100% SPY or 1x (100% SPY)"
        else:
            if treasury_rate and treasury_rate < 4:
                recommendation = "Risk ALT - 25% UPRO + 75% ZROZ or 1.5x (50% SPY + 50% ZROZ)"
            else:
                recommendation = "Risk OFF - 100% SPY or 1x (100% SPY)"
        
        embed.add_field(name="MFEA Recommendation", value=recommendation, inline=False)
        embed.set_footer(text="Use @MFEA bot#3562 to interact again.")
        await interaction.followup.send(embed=embed)
    except ValueError as e:
        await interaction.followup.send(f"Error fetching data: {e}")
    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred: {e}")

# Function to show commands
async def show_commands(interaction):
    embed = discord.Embed(title="MFEA Bot Commands", color=discord.Color.green())
    embed.add_field(name="@MFEA bot#3562", value="Shows this interactive interface.", inline=False)
    embed.add_field(name="Check Market Data", value="Fetches market data and provides recommendations.", inline=False)
    embed.add_field(name="Links", value="Provides a link to testfol.io.", inline=False)
    embed.add_field(name="Ping", value="Checks if the bot is online and responsive.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Flask setup for port binding
app = Flask(__name__)

@app.route("/")
def home():
    return "The bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if PORT is not set
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Ensure Flask thread exits when the main program exits
    flask_thread.start()

    # Start Discord bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
