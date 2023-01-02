# This bot requires the 'message_content' privileged intent to function.

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from models import engine, Session, Base, VisualNovel
from scheduler import Scheduler

load_dotenv()

DISCORD_API_KEY = os.environ['DISCORD_API_KEY']
ITCH_API_KEY = os.environ['ITCH_API_KEY']
ITCH_COLLECTION_ID = os.environ['ITCH_COLLECTION_ID']

Base.metadata.create_all(engine)
session = Session()

scheduler = Scheduler()
scheduler.run(ITCH_API_KEY, ITCH_COLLECTION_ID)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.command()
async def config(ctx, *args):
    await ctx.send('pong')


@bot.command()
async def search(ctx, *args):
    name = ' '.join(args)
    if name:
        visual_novels = session.query(VisualNovel) \
            .filter(VisualNovel.name.contains(name)) \
            .all()
        matches = len(visual_novels)
        if matches:
            result = f'Found {matches} matches for "{name}":\n'
            for visual_novel in visual_novels:
                result += f'{visual_novel.name}, Latest Version: {visual_novel.latest_version}, ' \
                          f'Last Updated At: <t:{int(visual_novel.updated_at)}:f> <{visual_novel.url}>\n'
        else:
            result = f'Found no matches for "{name}"'
    else:
        result = 'Usage: <command> <search term>'
    await ctx.send(result.strip())


bot.run(DISCORD_API_KEY)
