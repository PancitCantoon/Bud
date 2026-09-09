import asyncio
import os
import discord
from discord.ext import commands
from bud_alive import bud_alive
import httpx

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

afk_timers = {}

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

MEMBER_EMOJIS = {
    1522286617237262413: "<:sr:1546869522559012905>",
    495109290487709697: "<:ac:1546170236422856774>",
    919210874663747584: "<:ms:1546170279787634728>",
    1159418013091643442: "<:ms:1546170279787634728>",
    708998163859767376: "<:mp:1546170339917303870>",
    242629532580839424: "<:de:1546170383642656838>",
    566632140410716160: "<:ma:1546170426349068418>",
    824157691924447253: "<:mr:1546170474646736917>",
    1308381278470541345: "<:mr:1546170474646736917>",
    1044206400068407307: "<:sh:1546170590518312991>",
    960825861098057738: "<:mv:1546429844772884580>",
    1508032207548186635: "<:mv:1546429844772884580>",
    1099539902099624016: "<:me:1546170540119695410>",
    950039694274617375: "<:ch:1546170741085577296>",
    1285187681315192847: "<:mt:1546170777668296714>",
    865740000557006848: "<:mk:1546170925148541099>",
    720141452000231465: "<:my:1546170976386158762>",
    678432766236426241: "<:md:1546429613931102238>",
    709228195869622292: "<:mm:1546841316892348506>",
    835982359622189097: "<:ya:1546866714019631224>",
}

ROSTER_ORDER = [
    1522286617237262413,
    495109290487709697,   
    919210874663747584,   
    708998163859767376,   
    242629532580839424,   
    566632140410716160,   
    824157691924447253,   
    1044206400068407307,  
    960825861098057738,   
    1099539902099624016,  
    950039694274617375,   
    1285187681315192847,  
    865740000557006848,   
    720141452000231465,   
    678432766236426241,   
    709228195869622292,
    835982359622189097,
]

ALT_TO_MAIN = {
    1159418013091643442: 919210874663747584,
    960825861098057738: 1508032207548186635,
    824157691924447253: 1308381278470541345,
    1522286617237262413: 695247806658773053,
}

TARGET_VOICE_CHANNEL_IDS = {
    1270774306284245025,
    1480198294369075271,
    1507383877260279929,
    1522597436336509039,
    1434565402318602250,
    1536564360225361960,
}

async def update_voice_channel_status(channel, bot_token):
    if channel.id not in TARGET_VOICE_CHANNEL_IDS:
        return

    active_members = channel.members
    
    def get_sort_key(member):
        effective_id = ALT_TO_MAIN.get(member.id, member.id)
        if effective_id in ROSTER_ORDER:
            return ROSTER_ORDER.index(effective_id)
        return 999

    sorted_members = sorted(active_members, key=get_sort_key)

    emoji_lineup = []
    seen_emojis = set()
    
    for m in sorted_members:
        if m.id in MEMBER_EMOJIS:
            emoji = MEMBER_EMOJIS[m.id]
            if emoji not in seen_emojis:
                seen_emojis.add(emoji)
                emoji_lineup.append(emoji)

    status_text = " ".join(emoji_lineup) if emoji_lineup else ""

    url = f"https://discord.com/api/v10/channels/{channel.id}/voice-status"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"status": status_text}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            if response.status_code != 204:
                print(f"Failed to update status for {channel.name}: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"Error updating voice channel status for {channel.name}: {e}", flush=True)

async def afk_countdown(voice_client, channel, config):
    try:
        guild = channel.guild
        special_role_id = config.get("role_id") if config else None
        target_channel_id = config.get("channel_id") if config else None
 
        await asyncio.sleep(1200)
        
        real_users = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users) == 0:
            text_channel = guild.get_channel(target_channel_id) if target_channel_id else None
            if not text_channel:
                text_channel = discord.utils.get(guild.text_channels, name="general") or (guild.text_channels[0] if guild.text_channels else None)

            if text_channel:
                role_mention = f"<@&{special_role_id}>" if special_role_id else "@everyone"
                try:
                    await text_channel.send(f"{role_mention} Bud has been getting sleepy! Someone needs to join within 10 minutes or the call will disconnect")
                except discord.errors.HTTPException as e:
                    print(f"Failed to send 20-min warning due to rate limit: {e}")

        await asyncio.sleep(600)

        real_users_final = [m for m in channel.members if not m.bot]
        if voice_client.is_connected() and voice_client.channel == channel and len(real_users_final) == 0:
            text_channel = guild.get_channel(target_channel_id) if target_channel_id else None
            if not text_channel:
                text_channel = discord.utils.get(guild.text_channels, name="general") or (guild.text_channels[0] if guild.text_channels else None)
            if text_channel:
                try:
                    await text_channel.send("30 minutes are up. Bud is going for a nap")
                except discord.errors.HTTPException as e:
                    print(f"Failed to send final disconnect message due to rate limit: {e}")
            
            target_ch = voice_client.channel
            TOKEN = os.getenv('DISCORD_TOKEN')
            await voice_client.disconnect()
            if target_ch:
                await update_voice_channel_status(target_ch, TOKEN)

            if guild.id in afk_timers:
                del afk_timers[guild.id]

    except asyncio.CancelledError:
        pass
        
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id
    TOKEN = os.getenv('DISCORD_TOKEN')

    if before.channel:
        await update_voice_channel_status(before.channel, TOKEN)
    if after.channel and after.channel != before.channel:
        await update_voice_channel_status(after.channel, TOKEN)

    if member.id == bot.user.id:
        return

    if before.channel is not None and before.channel != after.channel:
        bot_in_guild = discord.utils.get(bot.voice_clients, guild=member.guild)
        if not bot_in_guild:
            real_users_left_behind = [m for m in before.channel.members if not m.bot]
            if len(real_users_left_behind) == 1:
                try:
                    voice_client = await before.channel.connect()
                    config = SERVER_CONFIGS.get(guild_id)
                    if guild_id in afk_timers:
                        afk_timers[guild_id]['task'].cancel()
                    task = bot.loop.create_task(afk_countdown(voice_client, before.channel, config))
                    afk_timers[guild_id] = {'task': task, 'channel_id': before.channel.id}
                    return
                except Exception as e:
                    print(f"Can't join channel upon user leaving {e} :(")

    if after.channel is not None:
        bot_in_guild = discord.utils.get(bot.voice_clients, guild=member.guild)
        if not bot_in_guild:
            real_users = [m for m in after.channel.members if not m.bot]
            if len(real_users) == 1:
                try:
                    voice_client = await after.channel.connect()
                    config = SERVER_CONFIGS.get(guild_id)
                    if guild_id in afk_timers:
                        afk_timers[guild_id]['task'].cancel()
                    task = bot.loop.create_task(afk_countdown(voice_client, after.channel, config))
                    afk_timers[guild_id] = {'task': task, 'channel_id': after.channel.id}
                    return
                except Exception as e:
                    print(f"Can't join channel {e} :(")

    for voice_client in list(bot.voice_clients):
        if voice_client.guild.id != guild_id:
            continue
            
        channel = voice_client.channel
        if channel is None:
            continue

        real_users_in_channel = [m for m in channel.members if not m.bot]

        if len(real_users_in_channel) >= 2:
            if guild_id in afk_timers:
                afk_timers[guild_id]['task'].cancel()
                del afk_timers[guild_id]
            left_channel = voice_client.channel
            await voice_client.disconnect()
            if left_channel:
                await update_voice_channel_status(left_channel, TOKEN)
            return

        if len(real_users_in_channel) == 0:
            if guild_id not in afk_timers:
                config = SERVER_CONFIGS.get(guild_id)
                task = bot.loop.create_task(afk_countdown(voice_client, channel, config))
                afk_timers[guild_id] = {'task': task, 'channel_id': channel.id}
        else:
            if guild_id in afk_timers:
                afk_timers[guild_id]['task'].cancel()
                del afk_timers[guild_id]
                
@bot.command()
async def join(ctx):
    """Joins the voice channel you are currently in."""
    guild_id = ctx.guild.id
    TOKEN = os.getenv('DISCORD_TOKEN')
    if ctx.author.voice:
        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            old_channel = ctx.voice_client.channel
            await ctx.voice_client.move_to(channel)
            if old_channel:
                await update_voice_channel_status(old_channel, TOKEN)
            await update_voice_channel_status(channel, TOKEN)
            return await ctx.send("I got you, bud")

        voice_client = await channel.connect()
        await update_voice_channel_status(channel, TOKEN)
        await ctx.send("I got you, bud")

        real_users = [m for m in channel.members if not m.bot]
        if len(real_users) <= 1:
            if guild_id in afk_timers:
                afk_timers[guild_id]['task'].cancel()
            config = SERVER_CONFIGS.get(guild_id)
            task = bot.loop.create_task(afk_countdown(voice_client, channel, config))
            afk_timers[guild_id] = {'task': task, 'channel_id': channel.id}
    else:
        await ctx.send("You need to be in a voice channel first, bud")

@bot.command()
async def leave(ctx):
    """Leaves the voice channel."""
    guild_id = ctx.guild.id
    TOKEN = os.getenv('DISCORD_TOKEN')
    if ctx.voice_client:
        if guild_id in afk_timers:
            afk_timers[guild_id]['task'].cancel()
            del afk_timers[guild_id]
        channel = ctx.voice_client.channel
        await ctx.guild.voice_client.disconnect()
        if channel:
            await update_voice_channel_status(channel, TOKEN)
        await ctx.send("Catch ya later, bud")
    else:
        await ctx.send("Me not in a voice channel right now, bud")

@bot.command()
async def refreshstatus(ctx):
    """Manually updates or clears the voice status of your current channel."""
    if ctx.author.voice and ctx.author.voice.channel:
        TOKEN = os.getenv('DISCORD_TOKEN')
        await update_voice_channel_status(ctx.author.voice.channel, TOKEN)
        await ctx.send("Status refreshed, bud!", delete_after=5)
    else:
        await ctx.send("You need to be in a voice channel first, bud")

bud_alive()

TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not found!")
else:
    bot.run(TOKEN)
