import asyncio
import os
import discord
from discord.ext import commands
from bud_alive import bud_alive

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to track ongoing timers: {guild_id: {'task': asyncio.Task, 'channel_id': int}}
afk_timers = {}

# Server-specific role IDs dictionary: {guild_id: role_id}
SERVER_ROLES = {
    1270774305705427014: 1543417376815579226, 
    1522593521096196256: 1543422556646932590  
}

async def afk_countdown(voice_client, channel, special_role_id):
    try:
        # Wait 20 minutes
        await asyncio.sleep(1200)
        
        # Verify that bud is still in the same channel and it's ONLY bud in the call
        real_users = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users) == 0:
            text_channel = discord.utils.get(channel.guild.text_channels, name="general")
            if not text_channel:
                text_channel = channel.guild.text_channels[0] if channel.guild.text_channels else None

            if text_channel:
                role_mention = f"<@&{special_role_id}>" if special_role_id else "@everyone"
                await text_channel.send(f"{role_mention} Bud has been getting sleepy! Someone needs to join within 10 minutes or the call will disconnect")

        # Wait the remaining 10 minutes (600 seconds)
        await asyncio.sleep(600)

        # Final check: if still connected and still empty, disconnect
        real_users_final = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users_final) == 0:
            text_channel = discord.utils.get(channel.guild.text_channels, name="general") or (channel.guild.text_channels[0] if channel.guild.text_channels else None)
            if text_channel:
                await text_channel.send("30 minutes are up. Bud is going for a nap")
            await voice_client.disconnect()

    except asyncio.CancelledError:
        pass

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id

    # Ignore the bot's own movements
    if member.id == bot.user.id:
        return

    # 1. Auto-join: If a user is now in a channel alone and the bot isn't connected anywhere in this guild
    if after.channel is not None:
        # Check if the bot is already connected in this specific server
        bot_in_guild = discord.utils.get(bot.voice_clients, guild=member.guild)
        if not bot_in_guild:
            real_users = [m for m in after.channel.members if not m.bot]
            if len(real_users) == 1:
                try:
                    voice_client = await after.channel.connect()
                    
                    # Check if the user left behind solo needs an AFK timer right away
                    SPECIAL_ROLE_ID = SERVER_ROLES.get(guild_id)
                    task = bot.loop.create_task(afk_countdown(voice_client, after.channel, SPECIAL_ROLE_ID))
                    afk_timers[guild_id] = {'task': task, 'channel_id': after.channel.id}
                    return
                except Exception as e:
                    print(f"Can't join {e} :(")

    # 2. Check current bot voice connections for leaving/timer rules
    for voice_client in list(bot.voice_clients):
        if voice_client.guild.id != guild_id:
            continue
            
        channel = voice_client.channel
        if channel is None:
            continue

        real_users_in_channel = [m for m in channel.members if not m.bot]

        # Disconnect immediately if 2 or more real users are in the bot's channel
        if len(real_users_in_channel) >= 2:
            if guild_id in afk_timers:
                afk_timers[guild_id]['task'].cancel()
                del afk_timers[guild_id]
            await voice_client.disconnect()
            return

        # If everyone left and it is now ONLY the bot in the channel, start the 30-min timer
        if len(real_users_in_channel) == 0:
            if guild_id not in afk_timers:
                # Look up the specific role ID for this server, default to None if not listed
                special_role_id = SERVER_ROLES.get(guild_id)
                task = bot.loop.create_task(afk_countdown(voice_client, channel, special_role_id))
                afk_timers[guild_id] = {'task': task, 'channel_id': channel.id}
        else:
            # If someone is still in the channel with the bot, cancel any active countdown
            if guild_id in afk_timers:
                afk_timers[guild_id]['task'].cancel()
                del afk_timers[guild_id]

@bot.command()
async def join(ctx):
    """Joins the voice channel you are currently in."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            return await ctx.send("I got you, bud")

        await channel.connect()
        await ctx.send("I got you, bud")
    else:
        await ctx.send("You need to be in a voice channel first, bud")

@bot.command()
async def leave(ctx):
    """Leaves the voice channel."""
    guild_id = ctx.guild.id
    if ctx.voice_client:
        if guild_id in afk_timers:
            afk_timers[guild_id]['task'].cancel()
            del afk_timers[guild_id]
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Catch ya later, bud")
    else:
        await ctx.send("Me not in a voice channel right now, bud")

# Start the background web server
bud_alive()

# Get the token from Render's Environment Variables safely
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not found!")
else:
    bot.run(TOKEN)
