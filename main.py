# This bot requires the 'message_content' privileged intent to function.

import os
import time

from discord.ext import commands, tasks
from models import engine, Session, Base, Game, User
from scheduler import Scheduler

DISCORD_API_KEY = os.environ['DISCORD_API_KEY']
ITCH_API_KEY = os.environ['ITCH_API_KEY']
ITCH_COLLECTION_ID = os.environ['ITCH_COLLECTION_ID']

Base.metadata.create_all(engine)

scheduler = Scheduler()
scheduler.run(ITCH_API_KEY, ITCH_COLLECTION_ID)

bot = commands.Bot()


@bot.event
async def on_ready():
    print('Bot is ready')
    if not notify_about_updates.is_running():
        notify_about_updates.start()


@tasks.loop(minutes=30)
async def notify_about_updates():
    print('[notify_about_updates] Start')
    await bot.wait_until_ready()
    with Session() as session:
        users = session.query(User)
        print('[notify_about_updates] User loop')
        for user in users:
            start_time = time.time()
            games = session.query(Game).filter(Game.updated_at > user.processed_at).order_by('name').all()
            if games:
                discord_user = bot.get_user(user.discord_id) or await bot.fetch_user(user.discord_id)
                result = f'Found {len(games)} new updates:\n'
                for game in games:
                    result += f'{game.name}, Latest Version: {game.latest_version}, ' \
                              f'Last Updated At: <t:{game.updated_at}:f> <{game.url}>\n'
                    if len(result) > 1600:
                        await discord_user.send(result)
                        result = ''
                if result:
                    await discord_user.send(result)
                user.processed_at = int(start_time)
                session.commit()


@bot.slash_command(name="subscribe")
async def subscribe(ctx):
    with Session() as session:
        user = session.query(User) \
            .filter(User.discord_id == ctx.author.id) \
            .first()
        if not user:
            # Start user off from point of subscription
            user = User(discord_id=ctx.author.id, processed_at=int(time.time()))
            session.add(user)
            session.commit()
            await ctx.respond('You\'ve subscribed to receive update infos.')
        else:
            await ctx.respond('You\'ve already subscribed to receive update infos.')


@bot.slash_command(name="unsubscribe")
async def unsubscribe(ctx):
    with Session() as session:
        user = session.query(User) \
            .filter(User.discord_id == ctx.author.id) \
            .first()
        if user:
            session.delete(user)
            session.commit()
            await ctx.respond('You\'ve unsubscribed from update infos.')
        else:
            await ctx.respond('You\'re not currently subscribed.')


@bot.slash_command(name="refresh")
async def refresh(ctx, name, refresh_version: bool = True, refresh_base_info: bool = False, refresh_tags: bool = False, force: bool = False):
    if name:
        with Session() as session:
            if force:
                games = session.query(Game) \
                    .filter(Game.name.contains(name)) \
                    .all()
            else:
                games = session.query(Game) \
                    .filter(Game.status != 'Abandoned', Game.status != 'Canceled', Game.name.contains(name)) \
                    .all()
            matches = len(games)
            if matches:
                await ctx.respond(f'Refreshing {matches} matches for "{name}"')
                for game in games:
                    if refresh_base_info:
                        game.refresh_base_info(ITCH_API_KEY)
                        session.commit()
                        time.sleep(10)
                    if refresh_tags:
                        game.refresh_tags_and_rating(ITCH_API_KEY, force)
                        session.commit()
                        time.sleep(10)
                    if refresh_version:
                        game.refresh_version(ITCH_API_KEY, force)
                        session.commit()
                        time.sleep(10)
            else:
                await ctx.respond(f'Found no matches for "{name}"')
    else:
        await ctx.respond('Usage: <command> <search term>')


@bot.slash_command(name="search")
async def search(ctx, name):
    if name:
        await ctx.defer()
        with Session as session:
            games = session.query(Game) \
                .filter(Game.name.contains(name)) \
                .all()
            matches = len(games)
            if matches:
                result = f'Found {matches} matches for "{name}":\n'
                for game in games:
                    if len(result) > 1600:
                        await ctx.send(result.strip())
                        result = ''
                    result += f'{game.name}, Latest Version: {game.latest_version}, ' \
                              f'Last Updated At: <t:{game.updated_at}:f> <{game.url}>\n'
            else:
                result = f'Found no matches for "{name}"'
    else:
        result = 'Usage: <command> <search term>'
    await ctx.followup.send(result.strip())


bot.run(DISCORD_API_KEY)
