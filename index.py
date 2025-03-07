# -*- coding: utf-8 -*-

# import
import importlib
import os
import discord
import discord.ext
from discord import app_commands
from dotenv import load_dotenv
load_dotenv()

# discord
intent = discord.Intents.default()
intent.emojis = True
intent.message_content = True
intent.messages = True
client = discord.Client(intents=intent)

# load all on message
extension_dir = 'on_message'
on_message_functions = []
for filename in os.listdir(extension_dir):
    if filename.endswith('.py'):
        module_name = f'{extension_dir}.{filename[:-3]}'
        module = importlib.import_module(module_name)
        if hasattr(module, 'main'):
            on_message_functions.append(module.main)

@client.event
async def on_message(message):
    global llmUserCooltime, llmIsRunning
    if message.guild == None:
        # reject DM
        return
    if message.content == None:
        # reject no message
        return
    if message.channel == None:
        # reject DM
        return
    if message.author == client.user:
        # reject echo
        return
    if message.author.bot == True:
        # reject bot
        return

    for i in on_message_functions:
        await i(message, client)

@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))

client.run(os.getenv("DISCORD_TOKEN"))
