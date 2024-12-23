import discord
from discord.ext import commands
import os

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
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
