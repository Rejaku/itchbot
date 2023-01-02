# This bot requires the 'message_content' privileged intent to function.

import os
import time

import discord
from discord.ext import commands, tasks
from models import engine, Session, Base, VisualNovel, User
from scheduler import Scheduler

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


@bot.event
async def on_ready():
    print('Bot is ready')
    notify_about_updates.start()


@tasks.loop(minutes=30)
async def notify_about_updates():
    await bot.wait_until_ready()
    users = session.query(User)
    for user in users:
        start_time = time.time()
        visual_novels = session.query(VisualNovel).filter(VisualNovel.updated_at > user.processed_at).order_by('name').all()
        if visual_novels:
            discord_user = bot.get_user(user.discord_id) or await bot.fetch_user(user.discord_id)
            result = f'Found {len(visual_novels)} new updates:\n'
            for visual_novel in visual_novels:
                result += f'{visual_novel.name}, Latest Version: {visual_novel.latest_version}, ' \
                          f'Last Updated At: <t:{visual_novel.updated_at}:f> <{visual_novel.url}>\n'
                if len(result) > 1600:
                    await discord_user.send(result)
                    result = ''
            if result:
                await discord_user.send(result)
            user.processed_at = int(start_time)
            session.commit()


@bot.command()
async def subscribe(ctx):
    user = session.query(User) \
        .filter(User.discord_id == ctx.author.id) \
        .first()
    if not user:
        # Start user off from point of subscription
        user = User(discord_id=ctx.author.id, processed_at=int(time.time()))
        session.add(user)
        session.commit()
        await ctx.send('You\'ve subscribed to receive update infos.')
    else:
        await ctx.send('You\'ve already subscribed to receive update infos.')


@bot.command()
async def unsubscribe(ctx):
    user = session.query(User) \
        .filter(User.discord_id == ctx.author.id) \
        .first()
    if user:
        session.delete(user)
        session.commit()
        await ctx.send('You\'ve unsubscribed from update infos.')
    else:
        await ctx.send('You\'re not currently subscribed.')


@bot.command()
async def refresh(ctx, *args):
    name = ' '.join(args)
    if name:
        visual_novels = session.query(VisualNovel) \
            .filter(VisualNovel.name.contains(name)) \
            .all()
        matches = len(visual_novels)
        if matches:
            for visual_novel in visual_novels:
                visual_novel.refresh_data(ITCH_API_KEY)
                session.commit()
            await search(ctx, name)
    else:
        await ctx.send(f'Found no matches for "{name}"')


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
                          f'Last Updated At: <t:{visual_novel.updated_at}:f> <{visual_novel.url}>\n'
        else:
            result = f'Found no matches for "{name}"'
    else:
        result = 'Usage: <command> <search term>'
    await ctx.send(result.strip())


bot.run(DISCORD_API_KEY)
