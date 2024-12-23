import discord
from discord.ext import commands
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
import threading

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask setup for port binding
app = Flask(__name__)

@app.route("/")
def home():
    return "The bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if PORT is not set
    app.run(host="0.0.0.0", port=port)

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

# Discord UI for button-based interaction
class MFEAView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Check Market Data", style=discord.ButtonStyle.primary)
    async def check_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fetching data... Please wait.", ephemeral=True)
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
            embed.set_footer(text="Try !commands for other commands.")
            await interaction.followup.send(embed=embed)
        except ValueError as e:
            await interaction.followup.send(f"Error fetching data: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

    @discord.ui.button(label="Commands", style=discord.ButtonStyle.secondary)
    async def commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="MFEA Bot Commands", color=discord.Color.green())
        embed.add_field(name="!check", value="Fetches market data and provides recommendations.", inline=False)
        embed.add_field(name="!commands", value="Shows this commands interface.", inline=False)
        embed.add_field(name="!links", value="Provides a link to testfol.io.", inline=False)
        embed.add_field(name="!ping", value="Checks if the bot is online and responsive.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Links", style=discord.ButtonStyle.link, url="https://testfol.io")
    async def links(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        await message.channel.send("Select an option below:", view=MFEAView())
    await bot.process_commands(message)

@bot.command()
async def check(ctx):
    await ctx.send("Fetching data... Please wait.")
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
        embed.set_footer(text="Try !commands for other commands.")
        await ctx.send(embed=embed)
    except ValueError as e:
        await ctx.send(f"Error fetching data: {e}")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")

@bot.command()
async def ping(ctx):
    await ctx.send("Bot is ready!")

if __name__ == "__main__":
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Ensure Flask thread exits when the main program exits
    flask_thread.start()
    
    # Start Discord bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
