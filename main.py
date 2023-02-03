import discord
import aiosqlite
from discord.ext import commands
import aiohttp
from datetime import datetime
from utils import *
import logging
from load_mal_user import *
import redis
from functools import wraps
from time import perf_counter
import pandas as pd
import torch
import sys
intents = discord.Intents.default()
intents.message_content = True
# intents.presences = True
sys.path.insert(0, './models')
db = redis.Redis(host='127.0.0.1', port=6666, db=0,decode_responses=True) #6666 for rocksdb, 6379 for redis
item_map = pd.read_csv("item_map.csv").set_index("item_id")
model = torch.load("models/multvae.pt",map_location=torch.device('cpu'))
model.eval()
bot = commands.Bot(command_prefix="/",intents=intents)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

rec = discord.SlashCommandGroup("rec", "Recommendation related commands")
mal = discord.SlashCommandGroup("mal", "MyAnimeList account configuration")

DELIM = "[split]"
INFO = open("long_messages/info.txt","r").read().split(DELIM)
TIPS = open("long_messages/tips.txt","r").read().split(DELIM)
FAQ = open("long_messages/faq.txt","r").read().split(DELIM)
"""
db format:
key: user
value: dict(
    keys: "mal", "recs", "mal_anime_ids","added_anime_ids,
    "bad_anime_ids" : this is a list of anime sthe user has seen, but not liked. we remove these from the recs
    values: mal username, set of recs, set of mal anime ids, set of manually added anime ids
)    
feedback will be stored in text
"""
last_heavy = dict() 

@bot.event
async def on_ready():
    global sqldb
    sqldb = await aiosqlite.connect("./animeinfo.sqlite3")
    await bot.change_presence(activity=discord.Game(name="DM me /info to begin!"))
    print(f'Logged on as {bot.user}!')

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    if error.isinstance(commands.CommandOnCooldown):
        await(ctx.respond(":stop_sign: " + str(error) + " :stop_sign:"))
    else:
        raise error

@bot.slash_command()
async def faq(ctx):
    flag = False
    for msg in FAQ:
        if flag:
            await ctx.send(msg)
        else:
            await ctx.respond(msg)
            flag = True

@bot.slash_command()
async def info(ctx):
    flag = False
    for msg in INFO:
        if flag:
            await ctx.send(msg)
        else:
            await ctx.respond(msg)
            flag = True
        
@bot.slash_command()
async def tips(ctx):
    flag = False
    for msg in TIPS:
        if flag:
            await ctx.send(msg)
        else:
            await ctx.respond(msg)
            flag = True

#OLD COOLDOWN FUNCTION
def check_cooldown(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        global last_heavy
        ctx = args[0]
        if ctx.author.id in last_heavy:
            if perf_counter() - last_heavy[ctx.author.id] < 10:
                await ctx.send("Please wait a few seconds before using this command again.")
                return
        start = perf_counter()
        await func(*args,**kwargs)
        logger.info(f"function {func.__name__} took {perf_counter() - start}")
        last_heavy[ctx.author.id] = perf_counter()
    return wrapper

def check_cooldown2(ctx):
    if ctx.author.id in last_heavy:
        if perf_counter() - last_heavy[ctx.author.id] < 3:
            raise commands.CommandOnCooldown("Please wait a few seconds before using this command again.")
    last_heavy[ctx.author.id] = perf_counter()
    return True

@mal.command(description="Set your MAL account.")
@commands.check(check_cooldown2)
async def set(ctx,username: discord.Option(str,description="MAL username",required=True)):
    # if not check_cooldown(ctx):
    #     await ctx.send("Please wait a few seconds before using this command again.")
    #     return
    await ctx.respond("This will take a moment...")
    session = aiohttp.ClientSession()
    a = await fetch_user(session,username)
    await session.close()
    if a['status'] != 200:
        await ctx.respond("Error retrieving data. Please check your username and try again.")
        return
    good,bad = get_liked_anime(a)
    if len(good) == 0:
        await ctx.respond("This user has no completed anime. Please add some manually with `/rec add <anime_title>`.")
        return
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:mal_anime_ids")
        pipe.delete(f"{ctx.author.id}:bad_anime_ids")
        pipe.set(f"{ctx.author.id}:mal",username)
        # pipe.set(f"{ctx.author.id}:mal_anime_ids",[])
        pipe.rpush(f"{ctx.author.id}:mal_anime_ids",*good)
        pipe.rpush(f"{ctx.author.id}:bad_anime_ids",*bad)
        pipe.execute()
    # last_heavy[ctx.author.id] = perf_counter()
    await ctx.send("Done!")

@mal.command(description="Remove your MAL account from the bot.")
async def remove(ctx):
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:mal")
        pipe.delete(f"{ctx.author.id}:mal_anime_ids")
        pipe.delete(f"{ctx.author.id}:bad_anime_ids")
        pipe.execute()
    await ctx.respond("Done!")
    
@bot.slash_command(description="Show your MAL and added animes.")
async def list(ctx):
    ids = [*db.smembers(f'{ctx.author.id}:added_anime_ids')]
    query = "select anime_title from anime_info where id in ({});".format(','.join(ids))
    output1 = await sqldb.execute(query)
    output = await output1.fetchall()
    content = "**MAL:** {}\n**Added Animes:\n**{}".format(db.get(f'{ctx.author.id}:mal'),'\n'.join([i[0] for i in output]))
    await ctx.respond(content)    

@rec.command(description="Clear your added animes.")
async def clear(ctx):
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:added_anime_ids")
        pipe.delete(f"{ctx.author.id}:added_anime_titles")
        pipe.execute()
    await ctx.respond("Done!")

@rec.command(description="Set default language for anime titles.")
async def lang(ctx,language: discord.Option(str)):
    if language not in ['en','jp']:
        await ctx.respond("MyAniRec supports English and Japanese. Please enter either `en` or `jp`.")
        return
    db.set(f"{ctx.author.id}:lang",language)
    await ctx.respond("Done! Keep in mind titles will default to Japanese if a translation is not available.")

@rec.command(description="Add an anime to your list.")
async def add(ctx,title: discord.Option(str,description="The title of the anime you want to add to your list.",required=True)):
    if len(title) == 0:
        await ctx.respond("Please enter the title of the anime you want to add. Ex. `/rec add Naruto`")
        return
    session = aiohttp.ClientSession()
    a = await fetch(session,title)
    await session.close()
    b = await formatlist(a)
    ##########################
    description = """Please send the number(s) for the anime(s) you are looking for. If none match, \
        send anything else and try `/rec add` again with more precise input.\n **Examples:**\
        `1 2 3` will add the first 3 animes to your list\n\
        `3` will add the third anime to your list"""
    embed = discord.Embed(title="Anime Search (Add)",description=description)
    embed.insert_field_at(0,name="Options",value=b,inline=False)
    embed.set_footer(text="If you changed your mind, please use the /rec remove command to remove it.")
    await ctx.respond(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    # print(msg.content)
    try:
        choices = [a[int(s)-1][1] for s in msg.content.split(" ") if s.isdigit()]
        db.sadd(f"{ctx.author.id}:added_anime_ids",*choices)  
        await ctx.send(f"Added {', '.join([a[int(s)-1][0] for s in msg.content.split(' ') if s.isdigit()])} to your list!")
    except Exception as e:
        logger.error(e)

async def process_recs(recs,language,start=1):
    #recs are item ids 
    # titles = item_map.loc[recs,"anime_title"].values
    lang_col = "english_title" if language == "en" else "anime_title"
    query = "select id,{},anime_title,score,genres from anime_info where id in ({});".format(lang_col,','.join(map(str,recs)))
    output = await sqldb.execute(query)
    df = pd.DataFrame(await output.fetchall(),columns=["id",lang_col,"anime_title_og","score","genres"]).set_index("id").loc[recs,:]
    ranks = pd.DataFrame(np.arange(start,start+len(recs)).reshape(-1,1),columns=["rank"],index=df.index)
    # print(ranks)
    # print(df)
    df = pd.concat([df,ranks],axis=1)
    df[lang_col] = df[lang_col].fillna(df["anime_title_og"])
    template = """__**{}: {}**__
> {}/10 :star: 
> Genres: {}"""
    templates = [template.format(df.loc[i,"rank"],
                                 f'[{df.loc[i,lang_col]}](https://myanimelist.net/anime/{i})',
                                 df.loc[i,"score"],
                                 ', '.join(df.loc[i,"genres"].split(";"))) for i in df.index]
    combined_templates = "\n\n".join(templates)
    embed = discord.Embed(title="Your Recommendations:",description=combined_templates,color=discord.Color(0x2e51a2))
    embed.set_footer(text="React (Double Click) using the arrows to browse more recommendations.")
    return embed
    

@rec.command(description="Get personalized recommendations based on your list.")
@commands.check(check_cooldown2)
async def complete(ctx):
    good_ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1)) #WHY IS THIS RETURNING STRINGS
    bad_ids = asint(db.lrange(f"{ctx.author.id}:bad_anime_ids",0,-1))
    
    #New ML logic
    session = aiohttp.ClientSession()
    ranks = await session.post("http://127.0.0.1:8000", json={"good": good_ids,"bad": bad_ids})
    ranks = await ranks.json()
    ranks = ranks['ranks']
    await session.close()
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:recs")
        pipe.rpush(f"{ctx.author.id}:recs",*(ranks))
        pipe.set(f"{ctx.author.id}:rec_offset",0)
        pipe.execute()
    recs = asint(db.lrange(f"{ctx.author.id}:recs",0,9)) #WHY IS THIS RETURNING STRINGS
    # print(recs)
    lang = db.get(f"{ctx.author.id}:lang")
    embed = await process_recs(recs,lang)
    message = await ctx.respond(embed=embed)
    original_message = await message.original_response()
    await original_message.add_reaction('◀️')
    await original_message.add_reaction('▶️')
    def check(payload):
        return payload.user_id == ctx.author.id and str(payload.emoji) in ['◀️','▶️']
    while True:
        try:
            # print("in")
            payload = await bot.wait_for('raw_reaction_add',check=check,timeout=360.0)
            emoji,user = payload.emoji,payload.user_id
            # print("in2")
            o = int(db.get(f"{ctx.author.id}:rec_offset"))
            if str(emoji) == '▶️':
                o = min(o+10,399)
            elif str(emoji) == '◀️':
                o = max(o-10,0)
            db.set(f"{ctx.author.id}:rec_offset",o)
            recs = asint(db.lrange(f"{ctx.author.id}:recs",o,o+9))
            embed = await process_recs(recs,lang,start=o+1)
            await original_message.edit(embed=embed)

        except asyncio.TimeoutError as e:
            # print(f"Timeout,{message.author.id}")
            # print(e)
            break

@rec.command(description="Remove an anime from your list.")
async def remove(ctx,title: discord.Option(str,description="The title of the anime you want to remove from your list.",required=True)):    
    # title = " ".join(titles)
    if len(title) == 0:
        await ctx.respond("Please enter the title of the anime you want to remove. Ex. `/rec remove Naruto`")
        return
    session = aiohttp.ClientSession()
    a = await fetch(session,title)
    await session.close()
    b = await formatlist(a)
    ##########################
    description = """Please send the number for the anime you are looking for. If none match, \
        send anything else and try `/rec remove` again with more precise spelling."""
    embed = discord.Embed(title="Anime Search (Remove)",description=description)
    embed.insert_field_at(0,name="Options",value=b,inline=False)
    embed.set_footer(text="If you changed your mind, please use the /rec remove command to remove it.")
    await ctx.respond(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    try:
        choices = [a[int(s)-1][1] for s in msg.content.split(" ") if s.isdigit()]
        db.srem(f"{ctx.author.id}:added_anime_ids",*choices)  
        await ctx.send(f"Removed {', '.join([a[int(s)-1][0] for s in msg.content.split(' ') if s.isdigit()])} from your list!")
    except Exception as e:
        logger.error(e)

@bot.slash_command(description="MAL anime ids of your list.")
async def myids(ctx):    
    ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1))
    await ctx.respond(str(ids))

@bot.slash_command(description="Submit feedback")
async def feedback(ctx, arg: discord.Option(str,name="feedback",required=True)): 
    # if len(args) > 1:
    #     await ctx.respond("Please enter your feedback surrounded by quotes, like so: `.feedback \"Stop being so good!\"`")   
    # text = args[0]
    with open("feedback.txt","a") as f:
        f.write(f"{ctx.author.id},{ctx.author.name},{ctx.guild},{str(datetime.now())},{arg}")
    await ctx.respond("Thank you for your feedback! The bot team might reach out to you if we have any questions.")
    
# @bot.slash_command()
# async def choice(ctx,*args): 
#     if len(args) > 1:
#         await ctx.respond("Please enter only one number, like so: `/choice 1`")   
#         return
#     c = int(args[0])
#     offset = int(db.get(f"{ctx.author.id}:rec_offset"))
#     anime_id = db.lindex(f"{ctx.author.id}:recs",offset+c-1)
#     with open("choices.txt","a") as f:
#         f.write(f"{ctx.author.id},{ctx.author.name},{ctx.guild},{str(datetime.now())},{offset-1},{anime_id},recs:{db.lrange(f'{ctx.author.id}:recs',0,-1)}")
#     await ctx.respond("Thank you for your input!")
# @bot.command()
# async def close(ctx):    
#     global sqldb
#     await sqldb.close()

TOKEN = open('token2.txt',"r").read()
print(TOKEN)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logger.addHandler(handler)
bot.add_application_command(rec)
bot.add_application_command(mal)
bot.run(TOKEN)