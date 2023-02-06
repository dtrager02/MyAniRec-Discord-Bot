import discord
from discord.ext import commands
import redis

class MyView(discord.ui.View):
    def add_select_options(self,options):
        self.options = []
        
    @discord.ui.select( # the decorator that lets you specify the properties of the select menu
        placeholder = "Choose an anime!", # the placeholder text that will be displayed if nothing is selected
        min_values = 1, # the minimum number of values that must be selected by the users
        max_values = 3, # the maximum number of values that can be selected by the users
        options = [ # the list of options from which users can choose, a required field
            discord.SelectOption(
                label="Vanilla",
                description="Pick this if you like vanilla!"
            ),
            discord.SelectOption(
                label="Chocolate",
                description="Pick this if you like chocolate!"
            ),
            discord.SelectOption(
                label="Strawberry",
                description="Pick this if you like strawberry!"
            )
        ]
    )
    async def select_callback(self, select, interaction): # the function called when the user is done selecting options
        select.disabled = True
        await interaction.response.send_message(f"Awesome! I like {select.values[0]} too!")
        
class MySelect(discord.ui.Select):
    def __init__(self,str_options=[],db=None,ctx=None,mode="add"):
        self.db = db
        self.ctx = ctx
        self.added = set()
        self.mode = mode
        self.a = str_options
        placeholder = "Choose some anime!" # the placeholder text that will be displayed if nothing is selected
        min_values = 1
        max_values = len(str_options) # the maximum number of values that can be selected by the users
        options = [discord.SelectOption(label=str_options[i][0],value=str(i)) for i in range(len(str_options))]
        super().__init__(placeholder=placeholder,min_values=min_values,max_values=max_values,options=options)
    async def callback(self, interaction): # the function called when the user is done selecting options
        # diff = set(self.values).difference(self.added)
        
        choices = [self.a[int(s)][1] for s in self.values]
        diff = set(self.values).difference(self.added) #self.added are indices from the array of [name,id]
        if self.mode == "add":
            self.db.sadd(f"{self.ctx.author.id}:added_anime_ids",*choices) 
            content = f"Added {', '.join([self.a[int(s)][0] for s in diff])} to your list!"
        elif self.mode == "remove":
            self.db.srem(f"{self.ctx.author.id}:added_anime_ids",*choices)  
            content = f"Removed {', '.join([self.a[int(s)][0] for s in diff])} from your list!"
        if len(diff):
            await interaction.response.send_message(content=content)#,view=discord.ui.View(self))
            self.added.update(diff)

            
        
        
    
