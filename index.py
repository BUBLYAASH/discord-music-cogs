#! /usr/bin/env python
# -*- coding: utf-8 -*-

import discord, random, os, requests
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
client = commands.Bot(command_prefix = PREFIX1,intents=intents)

async def on_ready():
    print("I'm ready to play good music!")
    client.load_extension('music')
    
@client.event
async def on_message(message):
    msg = message.content.lower()
    if str(msg) == '1' or str(msg) == '2' or str(msg) == '3' or str(msg) == '4' or str(msg) == '5' or str(
            msg) == '6' or str(msg) == '7' or str(msg) == '8' or str(msg) == '9' or str(msg) == '10' or str(
            msg) == 'cancel':
        for i in react:
            idi = str(i).split(':')
            if str(message.author.id) == idi[0]:
                react.remove(f'{idi[0]}:wait')
                react.append(f'{idi[0]}:{msg}')
                f = open('react.py', 'w')
                f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
                f.close()
                break
            else:
                pass
    await client.process_commands(message)

@client.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def load(ctx, extension):
    client.load_extension(f'{extension}')
    await ctx.send('Cogs loaded!', delete_after=5.0)

@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension):
    client.unload_extension(f'{extension}')
    await ctx.send(f"Cogs unloaded!", delete_after=5.0)

@client.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def reload(ctx, extension):
    client.reload_extension(f'{extension}')
    await ctx.send(f"Cogs reloaded!", delete_after=5.0)
    react.clear()
    f = open('react.py', 'w')
    f.write(f'#! /usr/bin/env python\n# -*- coding: utf-8 -*-\nreact = {str(react)}')
    f.close()

client.run(bot_token)