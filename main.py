import discord
from discord import app_commands

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')
@client.event
async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')    


TOKEN = open('token.txt',"r").read()

client.run(TOKEN)