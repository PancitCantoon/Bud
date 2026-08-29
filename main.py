import os
import discord
from discord.ext import commands
from bud_alive import bud_alive

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ')

@bot.command()
async def join(ctx):
    """Joins the voice channel you are currently in."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            return await ctx.send(f"Moved to {channel.name}.")

        await channel.connect()
        await ctx.send(f"Joined {channel.name}. I gotchu, bud.")
    else:
        await ctx.send("You need to be in a voice channel first so I know where to go!")

@bot.command()
async def leave(ctx):
    """Leaves the voice channel."""
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel right now.")

# Start the background web server
bud_alive()

# Get the token from Render's Environment Variables safely
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not found!")
else:
    bot.run(TOKEN)
