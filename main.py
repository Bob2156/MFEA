import discord
from discord.ext import commands
import os
import threading
from flask import Flask

# Flask web server for health checks
app = Flask(__name__)

@app.route("/")
def home():
    return "The bot is running!"

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_disconnect():
    print("Bot disconnected from Discord.")

@bot.event
async def on_resumed():
    print("Bot reconnected to Discord.")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

if __name__ == "__main__":
    # Run Flask server and Discord bot concurrently
    threading.Thread(target=run_flask).start()
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
