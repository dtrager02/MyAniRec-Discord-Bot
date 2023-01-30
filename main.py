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
# intents.message_content = True
# intents.presences = True
sys.path.insert(0, './models')
db = redis.Redis(host='127.0.0.1', port=6379, db=0,decode_responses=True)
item_map = pd.read_csv("item_map.csv").set_index("item_id")
model = torch.load("models/multvae.pt",map_location=torch.device('cpu'))
model.eval()
bot = commands.Bot(command_prefix="/",intents=intents)
DELIM = "[split]"
INFO = open("long_messages/info.txt","r").read().split(DELIM)
TIPS = open("long_messages/tips.txt","r").read().split(DELIM)
FAQ = open("long_messages/faq.txt","r").read().split(DELIM)
"""
db format:
key: user
value: dict(
    keys: "mal", "recs", "mal_anime_ids","added_anime_ids"
    values: mal username, set of recs, set of mal anime ids, set of manually added anime ids
)    
feedback will be stored in sqlite 
"""
last_heavy = dict() 
"""
db format:
key: user
value: last heavy command timestamp
"""
@bot.slash_command()
async def hello(ctx, name: str = None):
    name = name or ctx.author.name
    await ctx.respond(f"Hello {name}!")

@bot.event
async def on_ready():
    global sqldb
    sqldb = await aiosqlite.connect("./animeinfo.sqlite3")
    await bot.change_presence(activity=discord.Game(name="DM me /info to begin!"))
    print(f'Logged on as {bot.user}!')

@bot.group()
async def rec(ctx):
    pass

@bot.group()
async def mal(ctx):
    pass

@bot.command()
async def faq(ctx):
    for msg in FAQ:
        await ctx.send(msg)

@bot.command()
async def info(ctx):
    for msg in INFO:
        await ctx.send(msg)
        
@bot.command()
async def tips(ctx):
    for msg in TIPS:
        await ctx.send(msg)

def check_cooldown(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        global last_heavy
        ctx = args[0]
        if ctx.author.id in last_heavy:
            if perf_counter() - last_heavy[ctx.author.id] < 3:
                await ctx.send("Please wait a few seconds before using this command again.")
                return
        await func(*args,**kwargs)
        last_heavy[ctx.author.id] = perf_counter()
    return wrapper



@mal.command()
@check_cooldown
async def set(ctx,*args):
    # if not check_cooldown(ctx):
    #     await ctx.send("Please wait a few seconds before using this command again.")
    #     return
    if len(args) < 1:
        await ctx.send("Invalid arguments. See `/tips` for more info.")
        return
    username = args[0]
    await ctx.send("This will take a moment...")
    session = aiohttp.ClientSession()
    a = await fetch_user(session,username)
    if a['status'] != 200:
        await ctx.send("Error retrieving data. Please check your username and try again.")
        session.close()
        return
    good,bad = get_liked_anime(a)
    if len(good) == 0:
        await ctx.send("This user has no completed anime. Please add some manually with `/rec add <anime_title>`.")
        session.close()
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
    await session.close()
    await ctx.send("Done!")

@mal.command()
async def remove(ctx):
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:mal")
        pipe.delete(f"{ctx.author.id}:mal_anime_ids")
        pipe.delete(f"{ctx.author.id}:bad_anime_ids")
        pipe.execute()
    await ctx.send("Done!")
    
@bot.command()
async def list(ctx):
    ids = [*db.smembers(f'{ctx.author.id}:added_anime_ids')]
    query = "select anime_title from anime_info where id in ({});".format(','.join(ids))
    output1 = await sqldb.execute(query)
    output = await output1.fetchall()
    content = "**MAL:** {}\n**Added Animes:\n**{}".format(db.get(f'{ctx.author.id}:mal'),'\n'.join([i[0] for i in output]))
    await ctx.send(content)    

@rec.command()
async def clear(ctx):
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:added_anime_ids")
        pipe.delete(f"{ctx.author.id}:added_anime_titles")
        pipe.execute()
    await ctx.send("Done!")

@rec.command()
async def add(ctx,*args):
    title = " ".join(args)
    if len(title) == 0:
        await ctx.send("Please enter the title of the anime you want to add. Ex. `/rec add Naruto`")
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
    await ctx.send(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    try:
        choices = [a[int(s)-1][1] for s in msg.content.split(" ") if s.isdigit()]
        db.sadd(f"{ctx.author.id}:added_anime_ids",*choices)  
        await ctx.send(f"Added {', '.join([a[int(s)-1][0] for s in msg.content.split(' ') if s.isdigit()])} to your list!")
    except Exception as e:
        # print(e.with_traceback())
        ...

def process_recs(recs,start=1):
    titles = item_map.loc[recs,"anime_title"].values
    recs = [f'[{titles[i]}](https://myanimelist.net/anime/{recs[i]})' for i in range(len(titles))]
    description = formatlist2(recs,start)
    print(description)
    embed = discord.Embed(title="Your Recommendations:",description=description)
    embed.set_footer(text="React (Double Click) using the arrows to browse more recommendations.")
    return embed
    

@rec.command()
@check_cooldown
async def complete(ctx):
    good_ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1)) #WHY IS THIS RETURNING STRINGS
    bad_ids = asint(db.lrange(f"{ctx.author.id}:bad_anime_ids",0,-1))
    # Old ML logic
    # a = await generate_user_tensor(ids,item_map=item_map)
    # output,_,_ = model(a)
    # ranks = await get_ranking(output,item_map,ids)
    
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
    embed = process_recs(recs)
    message = await ctx.send(embed=embed)
    await message.add_reaction('◀️')
    await message.add_reaction('▶️')
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
            embed = process_recs(recs,start=o+1)
            await message.edit(embed=embed)

        except asyncio.TimeoutError as e:
            # print(f"Timeout,{message.author.id}")
            # print(e)
            break

@rec.command()
async def remove(ctx,*args):    
    title = " ".join(args)
    if len(title) == 0:
        await ctx.send("Please enter the title of the anime you want to remove. Ex. `/rec remove Naruto`")
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
    await ctx.send(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    try:
        choices = [a[int(s)-1][1] for s in msg.content.split(" ") if s.isdigit()]
        db.srem(f"{ctx.author.id}:added_anime_ids",*choices)  
        await ctx.send(f"Removed {', '.join([a[int(s)-1][0] for s in msg.content.split(' ') if s.isdigit()])} from your list!")
    except Exception as e:
        # print(e.with_traceback())
        ...

@bot.command()
async def myids(ctx,*args):    
    ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1))
    await ctx.send(str(ids))

@bot.command()
async def feedback(ctx,*args): 
    if len(args) > 1:
        await ctx.send("Please enter your feedback surrounded by quotes, like so: `.feedback \"Stop being so good!\"`")   
    text = args[0]
    with open("feedback.txt","a") as f:
        f.write(f"{ctx.author.id},{ctx.author.name},{ctx.guild},{str(datetime.now())},{text}")
    await ctx.send("Thank you for your feedback! The bot team might reach out to you if we have any questions.")
    
@bot.command()
async def choice(ctx,*args): 
    if len(args) > 1:
        await ctx.send("Please enter your feedback surrounded by quotes, like so: `.feedback \"Stop giving me exactly what I want!\"`")   
    c = int(args[0])
    offset = int(db.get(f"{ctx.author.id}:rec_offset"))
    anime_id = db.lindex(f"{ctx.author.id}:recs",offset+c-1)
    with open("choices.txt","a") as f:
        f.write(f"{ctx.author.id},{ctx.author.name},{ctx.guild},{str(datetime.now())},{offset-1},{anime_id},recs:{db.lrange(f'{ctx.author.id}:recs',0,-1)}")
    await ctx.send("Thank you for your input!")
# @bot.command()
# async def close(ctx):    
#     global sqldb
#     await sqldb.close()

TOKEN = open('token2.txt',"r").read()
print(TOKEN)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(TOKEN, log_handler=handler, log_level=logging.INFO)