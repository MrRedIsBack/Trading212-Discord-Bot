import requests, json, datetime

import os
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

import itertools

load_dotenv(dotenv_path="keys.env")

Trading212_APIKEY = str(os.getenv("Trading212_APIKEY"))
user_agent = str(os.getenv("user_agent"))

discord_bot_APIKEY = str(os.getenv("discord_bot_APIKEY"))

client = commands.Bot(command_prefix="!", intents = discord.Intents.all())

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@client.hybrid_command(name="portfolio", description = "Show your whole portfolio.")
async def portfolio(interaction: discord.Interaction):

    url = "https://live.trading212.com/api/v0/equity/account/cash"
    headers = {"Authorization": Trading212_APIKEY, "User-agent": user_agent}
    response = requests.get(url, headers=headers) #Gets the data from Trading212

    if response.status_code != 200:
        await interaction.reply(f"API is returning response {response.status_code}.", ephemeral = True)

    else:
        data = response.json()

        total = data["total"]
        invested = data["invested"]
        profit = data["ppl"]
        profit_percent = round((profit/invested)*100,2)
        pie_cash = data["pieCash"]

        portfolio_embed = discord.Embed(title = "Your Portfolio", colour = 0x3498db, timestamp=datetime.datetime.now())

        portfolio_embed.add_field(name="Total:", value = f"£{total:,}", inline=False)
        portfolio_embed.add_field(name="Invested:", value = f"£{invested:,}", inline=False)
        
        if profit < 0:
            portfolio_embed.add_field(name="Profit:", value = f"-£{abs(profit):,} ({profit_percent:,}%)", inline=False)

        else:
            portfolio_embed.add_field(name="Profit:", value = f"£{profit:,} ({profit_percent:,}%)", inline=False)

        portfolio_embed.add_field(name="Pie Cash:", value = f"£{pie_cash:,}", inline=False)

        await interaction.reply(embed = portfolio_embed, ephemeral = False)

class orders_view(discord.ui.View):

    def __init__(self, data, counter, first_click, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.counter = counter
        self.first_click = first_click

    @discord.ui.button(label = "\U0001F4CA", style = discord.ButtonStyle.blurple) #This is the button for the main overview embed which shows all orders, when the command is used, it should start on this embed
    async def overview_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.first_click = True #First click is a variable that keeps track if the arrows are being pressed for the "first time", because we want to return to the last order if we are on the overview embed

        new_embed = discord.Embed(title = "Your Orders", description = f"You hold {len(self.data)} orders, the below orders are based on pure profit.", colour = 0x3498db, timestamp=datetime.datetime.now())
        new_embed.add_field(name = "Your top 3 performers:", value = "\U0001F451 \U0001F451 \U0001F451", inline = False)

        ppl_leaderboard = {}
        for order in self.data: #We only want the ticker and the ppl, so we are creating a new dictionary just with that information
            ppl_leaderboard[order["ticker"]] = order["ppl"]

        ppl_leaderboard = dict(sorted(ppl_leaderboard.items(), key = lambda item: item[1], reverse = True)) #Sort the dictionary so that we have the top 3 orders by ppl

        for key,value in dict(itertools.islice(ppl_leaderboard.items(), 3)).items(): #Loop through the first 3 items and add them to the embed, using the itertools library 
            if value < 0:
                new_embed.add_field(name = key, value = f"-£{abs(value)}", inline = True)
            else:
                new_embed.add_field(name = key, value = f"£{value}", inline = True)

        new_embed.add_field(name = "Your worst 3 performers:", value = "\U0001F614 \U0001F614 \U0001F614", inline = False)

        ppl_leaderboard = dict(sorted(ppl_leaderboard.items(), key = lambda item: item[1], reverse = False)) #Sort the same dictionary again but now the opposite way

        for key,value in dict(itertools.islice(ppl_leaderboard.items(), 3)).items(): #Loop through the first 3 items and add them to the embed, using the itertools library 
            if value < 0:
                new_embed.add_field(name = key, value = f"-£{abs(value)}", inline = True)
            else:
                new_embed.add_field(name = key, value = f"£{value}", inline = True)

        await interaction.response.edit_message(embed = new_embed, view = orders_view(data=self.data, counter=self.counter, first_click=self.first_click))

    @discord.ui.button(label = "\U00002B05", style = discord.ButtonStyle.blurple) #This is the button to go back by 1 order
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.first_click == False: #If it is not the first click, then we do not want to be on order 1, so we -1 so we can go back to the previous order
            if self.counter == 0: #Checking to make sure we are not "out of the loop"
                self.counter = len(self.data) - 1 #Go to the last order in the list since we hit the end of the list

            else:
                self.counter -= 1 #If we are still in the loop then we can go back 1 order

            current_order = self.data[self.counter]
            current_order_ticker = current_order["ticker"]

            new_embed = discord.Embed(title = f"Order: {current_order_ticker}", colour = 0x3498db, timestamp=datetime.datetime.now())
            new_embed.set_footer(text = f"Order {self.counter + 1}/{len(self.data)}")

        else: #This is when the first click is true, so we want to be on the same order as we were previously, or on order 1 if we just ran /orders
            current_order = self.data[self.counter]
            current_order_ticker = current_order["ticker"]

            new_embed = discord.Embed(title = f"Order: {current_order_ticker}", colour = 0x3498db, timestamp=datetime.datetime.now())
            new_embed.set_footer(text = f"Order {self.counter + 1}/{len(self.data)}")

        current_order_quantity = current_order["quantity"]
        current_order_avgprice = current_order["averagePrice"]
        current_order_price = current_order["currentPrice"]
        current_order_ppl = current_order["ppl"]

        new_embed.add_field(name = "Quantity:", value = f"{current_order_quantity:,}", inline = False)
        new_embed.add_field(name = "Average Price:", value = f"£{current_order_avgprice:,}", inline = False)
        new_embed.add_field(name = "Current Price:", value = f"£{current_order_price:,}", inline = False)

        if current_order_ppl < 0:
            new_embed.add_field(name = "Profit:", value = f"-£{abs(current_order_ppl)}")

        else:
            new_embed.add_field(name = "Profit:", value = f"£{current_order_ppl}")

        self.first_click = False

        await interaction.response.edit_message(embed = new_embed, view = orders_view(data=self.data, counter=self.counter, first_click=self.first_click))

    @discord.ui.button(label = "\U000027A1", style = discord.ButtonStyle.blurple) #This is the button to go forward by 1 order.
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.first_click == False: #If it is not the first click, then we do not want to be on order 1, so we +1 so we can go to the next order
            if self.counter >= len(self.data)-1: #Checking to make sure we are not "out of the loop"
                self.counter = 0 #If we hit the end of the list of orders, we want to go back to the start

            else:
                self.counter += 1 #If we are still in the loop then we can go forward by 1 order

            current_order = self.data[self.counter]
            current_order_ticker = current_order["ticker"]

            new_embed = discord.Embed(title = f"Order: {current_order_ticker}", colour = 0x3498db, timestamp=datetime.datetime.now())
            new_embed.set_footer(text = f"Order {self.counter + 1}/{len(self.data)}")

        else:
            current_order = self.data[self.counter]
            current_order_ticker = current_order["ticker"]

            new_embed = discord.Embed(title = f"Order: {current_order_ticker}", colour = 0x3498db, timestamp=datetime.datetime.now())
            new_embed.set_footer(text = f"Order {self.counter + 1}/{len(self.data)}")

        current_order_quantity = current_order["quantity"]
        current_order_avgprice = current_order["averagePrice"]
        current_order_price = current_order["currentPrice"]
        current_order_ppl = current_order["ppl"]

        new_embed.add_field(name = "Quantity:", value = f"{current_order_quantity:,}", inline = False)
        new_embed.add_field(name = "Average Price:", value = f"£{current_order_avgprice:,}", inline = False)
        new_embed.add_field(name = "Current Price:", value = f"£{current_order_price:,}", inline = False)

        if current_order_ppl < 0:
            new_embed.add_field(name = "Profit:", value = f"-£{abs(current_order_ppl)}")

        else:
            new_embed.add_field(name = "Profit:", value = f"£{current_order_ppl}")

        self.first_click = False

        await interaction.response.edit_message(embed = new_embed, view = orders_view(data=self.data, counter=self.counter, first_click=self.first_click))

@client.hybrid_command(name = "orders", description = "Get a list of all your orders.")
async def orders(interaction: discord.Interaction):

    url = "https://live.trading212.com/api/v0/equity/portfolio"
    headers = {"Authorization": Trading212_APIKEY, "User-agent": user_agent}
    response = requests.get(url, headers=headers) #Gets the data from Trading212, we only get it once since trading212 API only allows 1 request every 30s

    if response.status_code != 200: #Checking to make sure that the API response is good
        await interaction.reply(f"API is returning response {response.status_code}.", ephemeral = True)

    else:
        counter = 0 #Keep track of which order we are on so we can loop through them
        first_click = True #First click is a variable that keeps track if the arrows are being pressed for the "first time", because we want to return to the last order if we are on the overview embed, since if this wasn't there, we wouldn't be on the first order

        data = response.json()

        orders_embed = discord.Embed(title = "Your Orders", description = f"You hold {len(data)} orders, the below orders are based on pure profit.", colour = 0x3498db, timestamp=datetime.datetime.now())
        orders_embed.add_field(name = "Your top 3 performers:", value = "\U0001F451 \U0001F451 \U0001F451", inline = False)

        ppl_leaderboard = {}
        for order in data: #We only want the ticker and the ppl, so we are creating a new dictionary just with that information
            ppl_leaderboard[order["ticker"]] = order["ppl"]

        ppl_leaderboard = dict(sorted(ppl_leaderboard.items(), key = lambda item: item[1], reverse = True)) #Sort the dictionary so that we have the top 3 orders by ppl

        for key,value in dict(itertools.islice(ppl_leaderboard.items(), 3)).items(): #Loop through the first 3 items and add them to the embed, using the itertools library 
            if value < 0:
                orders_embed.add_field(name = key, value = f"-£{abs(value)}", inline = True)
            else:
                orders_embed.add_field(name = key, value = f"£{value}", inline = True)

        orders_embed.add_field(name = "Your worst 3 performers:", value = "\U0001F614 \U0001F614 \U0001F614", inline = False)

        ppl_leaderboard = dict(sorted(ppl_leaderboard.items(), key = lambda item: item[1], reverse = False)) #Sort the dictionary again but now the opposite way

        for key,value in dict(itertools.islice(ppl_leaderboard.items(), 3)).items(): #Loop through the first 3 items and add them to the embed, using the itertools library 
            if value < 0:
                orders_embed.add_field(name = key, value = f"-£{abs(value)}", inline = True)
            else:
                orders_embed.add_field(name = key, value = f"£{value}", inline = True)

        await interaction.reply(embed = orders_embed, ephemeral = False, view = orders_view(data, counter, first_click))

@client.hybrid_command(name = "kill", description = "Kill the bot.")
@commands.is_owner()
async def kill(interaction: discord.Interaction):
    await interaction.reply("Bot is being shut down.", ephemeral=True)
    await client.close()
    print("Bot has been killed.")

client.run(discord_bot_APIKEY)
