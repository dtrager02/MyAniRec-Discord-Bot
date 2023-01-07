import discord
import aiosqlite
from discord.ext import commands
import aiohttp
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
intents.presences = True
sys.path.insert(0, './models')
db = redis.Redis(host='127.0.0.1', port=6379, db=0,decode_responses=True)
item_map = pd.read_csv("item_map.csv").set_index("item_id")
model = torch.load("models/multvae.pt",map_location=torch.device('cpu'))
model.eval()
bot = commands.Bot(command_prefix="/",intents=intents)
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
@bot.event
async def on_ready():
    global sqldb
    sqldb = await aiosqlite.connect("./animeinfo.sqlite3")
    await bot.change_presence(activity=discord.Game(name="DM me .info to begin!"))
    print(f'Logged on as {bot.user}!')

@bot.group()
async def rec(ctx):
    pass

@bot.group()
async def mal(ctx):
    pass

@bot.command()
async def faq(ctx):
    msg1 = """**Q:** How does it work?
**A:** Short Answer: A machine learning model developed by Netflix called MultVAE, a data management system called Redis, and a discord botwritten in Python. As far as I know, it is the first anime recommender system of this scale.
Long Answer, the model driving the system uses a Variational Autoencoder to learn the latent features of each item. It does so basically by feeding in over 50 million anime lists, calculating how closely the model predicted the items you watched, and updating themodel to optimize its predictions. When you use the bot, every anime you input is fed into the model, and the model outputs a ranking forevery other anime you haven't seen. The ranking is based on how likely that anime is to be in your list, and that is one of the limitationsof this kind of model - it cannot take into account changing preferences over time. It also struggles when a list contains very unpopularitems, or items that do not make sense to be together (e.g. seeing season 3 and 4 of a show, but not season 1). The model is still indevelopment, and I am constantly working on improving it.\n
**Q:** What anime should I add? The model works best if you add animes that you watched and had a positive experience with. Adding shows that you watched but meant nothing to you or shows you disliked will only hurt the performance of the current model. Also, adding strange combinations of shows, such as only season 4's with no season 1's sometimes lead to unpredictable results.
**A:**\n
**Q:** Where are the new anime?
**A:** This bot aims to have recommendations for all shows **up to the previous completed season.** Basically, the model behind this recommender system is enormous, and I cannot afford to update it every day as new shows and new ratings come out, nor would that beeffective given how ratings change drastically throughout the season.\n
**Q:** I found a bug, what do I do?
**A:** Message NoSkillOrHacks#9465 on discord, and we can work through it together. Otherwise, just use the `.feedback` command to let me know.\n\n"""
    msg2 = """**Q:** Why am I getting terrible Recommendations?
**A:** (Copium warning) There are many weaknesses of this kind of Recommender System. It struggles when a list contains very unpopular items, oritems that do not make sense to be together (e.g. seeing season 3 and 4 of a show, but not season 1). If you take the time to tune yourlist with the bot commands, it will definetely give better output. However, there is more. The model is only as good as the data it is fed.MyAnimeList, the website which I pulled over 50M users' public data from, has had issues historically with bots, review bombers, and othermalicious accounts. This kind of data obviously hurts the performance of the model. I did my best with common sense to filter out theseusers, but there is a very good chance a lot were still in the data. Also, unlike most recommender systems you are used to, this one(intentionally) has no inherent popularity filter. Compared to the top shows you usually hear about, there are at least 10 times moreunheard-of, and especially outdated shows. This means, by random chance, animes that nobody has ever heard of will end up at the top of therecommendations. That's just how probability works. Of course, some of these problems can be worked on, and I plan to keep updating theproject. Overall, I am happy with its recommendations so far.\n
"""
    await ctx.send(msg1)
    await ctx.send(msg2)

@bot.command()
async def info(ctx,*args):
    await ctx.send("""MyAniRec is a discord bot that will help you find anime recommendations based on your preferences. It runs an ML model trained on over 50 million users from myanimelist.net.
**Step 1 (Suggested):**\nUse the `.mal set <username>` command to set your MAL account username.
This will load all of your completed anime into the system and is much easier than typing them in one by one.
**Step 2 (Optional):**\nUse the `.rec add <anime_title>` command to add more anime to the list in case you don't have a MAL account or it is outdated. `<anime_title>` can be just part of the title, and the spelling doesn't have to be perfect either.
The more anime you add, the better the recommendations will be. See `.tips` for how to remove anime from the list.
**Step 3:**\nUse the `.rec complete` command to get recommendations.
**Step 4 (Optional):**\nUse the `.choose <number>` command to indicate which recommendation appealed to you the most.
This feedback will help me improve the bot and recommender system greatly!
**Step 5 (Optional):**\nUse the `.feedback "<>"` command to give feedback on the recommendations and/or bot. (Make sure to use quotes)\n
Keep in mind the bot will remember all your input, so no need to repeat old commands unless you want to change something. 
Speaking of changing input, are several other useful commands for managing your anime list and recommendations. Enter `.tips` to find them. Also check out `.faq` if you are confused.""")
    
@bot.command()
async def tips(ctx):
    await ctx.send("""**Timeouts:** For 'heavy' commands like `.rec complete` and `.mal set`, you must wait **3 seconds** between each command. 
Most other commands will have virtually  no limit, so spam away.
For some other commands that involve multiple inputs, the bot will stop waiting for inputs after **6 minutes**. Youalways restart the command if you need to. 
**Saving:** The bot will remember all your input, so no need to repeat old commands unless you want to change something. 
**Commands:** <> indicates a required input, [] indicates an optional input*. You do not need to literally input symbols. All unrequired input will be ignored.
`.mal set <username>`: Set your MAL username. This will load all of your completed anime into the system and is much eathan typing them in one by one.
`.mal remove`: Delete all your MAL data. If you use this, the anime you manually entered with the .rec command will still be there, so it is useful if you like manual tuning without MAL.
`.rec add <anime_title>`: Add an anime to your list. Follow the directions in the bot's response. You will be able to add multiple at once by inputting the numbers separated by spaces.
`.rec remove <anime_title>`: Remove an anime from your list. Follow the directions in the bot's response. Due to the way the bot works, there is no way to remove an anime from a linked MAL account. If you don't like certain ratings in your MAL, do `.mal remove` and manually add them back with `.rec add`, or simply update your MAL account.
`.rec complete`: Get recommendations. Follow the directions in the bot's response to see more pages of recommendations.
`.list`: Lists all the data the bot has on you. This is useful for making sure you are ready before `.rec complete`.
""")
    await ctx.send("""`.tips`: Shows this message.
`.faq`: Shows frequently asked questions and background info about this bot.
`.info`: Shows a short description of the bot and how to use it.
`.myids`: Shows all MAL anime ids that the bot has on you. This is useful for debugging.
`.feedback`: TODO
`.choose <number>`: TODO
""")
#rec remove
#list
#restart    
#tips
#choose
# feedback
# about
# faq 
#TODO
#possibly persist requests session
#add caching for recs if no input has changed
#persist redis db and handle large data, large discord logs
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
        await ctx.send("Invalid arguments. See `.tips` for more info.")
        return
    username = args[0]
    await ctx.send("This will take a moment...")
    session = aiohttp.ClientSession()
    a = await fetch_user(session,username)
    if a['status'] != 200:
        await ctx.send("Error retrieving data. Please check your username and try again.")
    b = get_liked_anime(a)
    if len(b) == 0:
        await ctx.send("This user has no completed anime. Please add some manually with `.rec add <anime_title>`.")
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:mal_anime_ids")
        pipe.set(f"{ctx.author.id}:mal",username)
        # pipe.set(f"{ctx.author.id}:mal_anime_ids",[])
        pipe.rpush(f"{ctx.author.id}:mal_anime_ids",*b)
        pipe.execute()
    # last_heavy[ctx.author.id] = perf_counter()
    await session.close()
    await ctx.send("Done!")

@mal.command()
async def remove(ctx):
    with db.pipeline() as pipe:
        pipe.delete(f"{ctx.author.id}:mal")
        pipe.delete(f"{ctx.author.id}:mal_anime_ids")
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
async def add(ctx,*args):
    title = " ".join(args)
    if len(title) == 0:
        await ctx.send("Please enter the title of the anime you want to add. Ex. `.rec add Naruto`")
        return
    session = aiohttp.ClientSession()
    a = await fetch(session,title)
    b = await formatlist(a)
    ##########################
    description = """Please send the number(s) for the anime(s) you are looking for. If none match, \
        send anything else and try `.rec add` again with more precise input.\n **Examples:**\
        `1 2 3` will add the first 3 animes to your list\n\
        `3` will add thethird anime to your list"""
    embed = discord.Embed(title="Anime Search (Add)",description=description)
    embed.insert_field_at(0,name="Options",value=b,inline=False)
    embed.set_footer(text="If you changed your mind, please use the .rec remove command to remove it.")
    await ctx.send(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    try:
        choices = [a[int(s)-1][1] for s in msg.content.split(" ") if s.isdigit()]
        db.sadd(f"{ctx.author.id}:added_anime_ids",*choices)  
        await ctx.send(f"Added {','.join([a[int(s)-1][0] for s in msg.content.split(' ') if s.isdigit()])} to your list!")
    except Exception as e:
        # print(e.with_traceback())
        ...
    await session.close()

def process_recs(recs):
    titles = item_map.loc[recs,"anime_title"].values
    recs = [f'[{titles[i]}](https://myanimelist.net/anime/{recs[i]})' for i in range(len(titles))]
    description = formatlist2(recs)
    print(description)
    embed = discord.Embed(title="Your Recommendations:",description=description)
    embed.set_footer(text="React using the arrows to browse more recommendations.")
    return embed
    

@rec.command()
@check_cooldown
async def complete(ctx):
    ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1)) #WHY IS THIS RETURNING STRINGS
    a = await generate_user_tensor(ids,item_map=item_map)
    output,_,_ = model(a)
    # print("hi")
    ranks = await get_ranking(output,item_map,ids)
    # print(ranks[:10])
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
            
            # await message.remove_reaction(emoji,payload.member)
            embed = process_recs(recs)
            await message.edit(embed=embed)
            # await message.add_reaction('◀️')
            # await message.add_reaction('▶️')
        except asyncio.TimeoutError as e:
            # print(f"Timeout,{message.author.id}")
            # print(e)
            break

@rec.command()
async def remove(ctx,*args):    
    title = " ".join(args)
    if len(title) == 0:
        await ctx.send("Please enter the title of the anime you want to remove. Ex. `.rec remove Naruto`")
    session = aiohttp.ClientSession()
    a = await fetch(session,title)
    b = await formatlist(a)
    ##########################
    description = """Please send the number for the anime you are looking for. If none match, \
        send anything else and try `.rec add` again with more precise spelling."""
    embed = discord.Embed(title="Anime Search (Remove)",description=description)
    embed.insert_field_at(0,name="Options",value=b,inline=False)
    embed.set_footer(text="If you changed your mind, please use the .rec remove command to remove it.")
    await ctx.send(embed=embed)
    ##########################
    msg = await bot.wait_for('message',check=lambda message: message.author == ctx.author,timeout=360.0)
    try:
        choice = int(msg.content)
        db.srem(f"{ctx.author.id}:added_anime_ids",a[choice-1][1])  
        await ctx.send(f"Removed {a[choice-1][0]} from your list!")
    except Exception as e:
        # print(e.with_traceback())
        ...
    await session.close()

@bot.command()
async def myids(ctx,*args):    
    ids = asint(db.smembers(f'{ctx.author.id}:added_anime_ids')) +  asint(db.lrange(f"{ctx.author.id}:mal_anime_ids",0,-1))
    await ctx.send(str(ids))

# @bot.command()
# async def close(ctx):    
#     global sqldb
#     await sqldb.close()
TOKEN = open('token.txt',"r").read()
print(TOKEN)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(TOKEN, log_handler=handler, log_level=logging.INFO)