import os
import discord
from discord.ext import commands
from bud_alive import bud_alive
import httpx

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_VOICE_CHANNEL_IDS = {
    1270774306284245025,
    1536564360225361960,
    1507383877260279929,
    1522597436336509039,
    1480198294369075271,
    1434565402318602250,
    1552638153721122966,
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
    411916947773587456: "<:jockie:1547313729727631491>", 
    513423712582762502: "<:tts:1547313797742596136>", 
}

ROSTER_ORDER = [
    1543053182110924810,
    513423712582762502,
    411916947773587456,
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
    1508032207548186635: 960825861098057738,
    1308381278470541345: 824157691924447253,
    695247806658773053: 1522286617237262413,
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

    status_text = "".join(emoji_lineup) if emoji_lineup else ""

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    TOKEN = os.getenv('DISCORD_TOKEN')

    if before.channel:
        await update_voice_channel_status(before.channel, TOKEN)
    if after.channel and after.channel != before.channel:
        await update_voice_channel_status(after.channel, TOKEN)

@bot.command()
async def refreshstatus(ctx):
    """Manually updates or clears the voice status of your current channel."""
    if ctx.author.voice and ctx.author.voice.channel:
        TOKEN = os.getenv('DISCORD_TOKEN')
        await update_voice_channel_status(ctx.author.voice.channel, TOKEN)
        await ctx.send("Status refreshed!", delete_after=5)
    else:
        await ctx.send("You need to be in a voice channel first, bud")

bud_alive()

TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not found!")
else:
    bot.run(TOKEN)
