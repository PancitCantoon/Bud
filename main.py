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

# Server configurations: {guild_id: {"role_id": int, "channel_id": int}}
SERVER_CONFIGS = {
    1270774305705427014: {
        "role_id": 1543417376815579226, 
        "channel_id": 1436411405640405082
    },  
    1522593521096196256: {
        "role_id": 1543422556646932590, 
        "channel_id": 1524063080290713711
    }   
}

async def afk_countdown(voice_client, channel, config):
    try:
        guild = channel.guild
        special_role_id = config.get("role_id") if config else None
        target_channel_id = config.get("channel_id") if config else None

        # Wait 20 minutes 
        await asyncio.sleep(1200)
        
        # Verify that bud is still in the same channel and it's ONLY the bot
        real_users = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users) == 0:
            text_channel = guild.get_channel(target_channel_id) if target_channel_id else None
            if not text_channel:
                text_channel = discord.utils.get(guild.text_channels, name="general") or (guild.text_channels[0] if guild.text_channels else None)

            if text_channel:
                role_mention = f"<@&{special_role_id}>" if special_role_id else "@everyone"
                await text_channel.send(f"{role_mention} Bud has been getting sleepy! Someone needs to join within 10 minutes or the call will disconnect")

        # Wait the remaining 10 minutes
        await asyncio.sleep(600)

        # Final check: if still connected and still empty, disconnect
        real_users_final = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users_final) == 0:
            text_channel = guild.get_channel(target_channel_id) if target_channel_id else None
            if not text_channel:
                text_channel = discord.utils.get(guild.text_channels, name="general") or (guild.text_channels[0] if guild.text_channels else None)
            if text_channel:
                await text_channel.send("30 minutes are up. Bud is going for a nap")
            await voice_client.disconnect()

    except asyncio.CancelledError:
        pass
        
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    # Broadcast update patch notes to all configured servers upon startup
    for guild_id, config in SERVER_CONFIGS.items():
        guild = bot.get_guild(guild_id)
        if guild:
            target_channel_id = config.get("channel_id")
            text_channel = guild.get_channel(target_channel_id) if target_channel_id else None
            if not text_channel:
                text_channel = discord.utils.get(guild.text_channels, name="general") or (guild.text_channels[0] if guild.text_channels else None)
            
            if text_channel:
                patch_notes = (
                    "**Bud Update: What's new and what's changed**\n\n"
                    "• **Auto-Join:** Bud will now automatically jump into a voice channel the second someone joins it completely solo or when someone is left alone.\n"
                    "• **Auto-Leave:** If a second user joins the call, Bud immediately leaves.\n"
                    "• **30-Minute AFK Fail-Safe:** If everyone leaves and Bud is alone in an empty channel, a 30-minute timer starts. At 20 minutes, it sends a warning, and at 30 minutes, it promptly disconnects."
                )
                try:
                    await text_channel.send(patch_notes)
                except Exception as e:
                    print(f"Could not send patch notes to guild {guild.name}: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id

    # Ignore the bot's own movements
    if member.id == bot.user.id:
        return

    # 1. Auto-join: If a user is now in a channel alone and the bot isn't connected in this guild
    if after.channel is not None:
        bot_in_guild = discord.utils.get(bot.voice_clients, guild=member.guild)
        if not bot_in_guild:
            real_users = [m for m in after.channel.members if not m.bot]
            if len(real_users) == 1:
                try:
                    await after.channel.connect()
                    return
                except Exception as e:
                    print(f"Could not auto-join channel: {e}")

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
                config = SERVER_CONFIGS.get(guild_id)
                task = bot.loop.create_task(afk_countdown(voice_client, channel, config))
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
