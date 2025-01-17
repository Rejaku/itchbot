# This bot requires the 'message_content' privileged intent to function.
import datetime
import os
import time

from discord.ext import commands, tasks
from models import Session, Game, User, GameVersion

DISCORD_API_KEY = os.environ['DISCORD_API_KEY']
DISCORD_ADMIN_ID = os.environ['DISCORD_ADMIN_ID']
DISCORD_NOTIFICATIONS_CHANNEL_ID = os.environ['DISCORD_NOTIFICATIONS_CHANNEL_ID']

bot = commands.Bot()


@bot.event
async def on_ready():
    print('Bot is ready')
    if not notify_about_updates.is_running():
        notify_about_updates.start()


@tasks.loop(minutes=30)
async def notify_about_updates():
    print("\n[notify_about_updates] Start\n")
    await bot.wait_until_ready()
    with Session() as session:
        users = session.query(User)
        print("\n[notify_about_updates] User loop\n")
        for user in users:
            start_time = datetime.datetime.utcnow()
            game_versions = session.query(
                Game, GameVersion
            ).join(
                Game, GameVersion.game_id == Game.id
            ).filter(
                Game.is_visible == True,
                GameVersion.created_at > user.processed_at,
                GameVersion.is_latest == True
            ).order_by(
                Game.name
            ).all()
            if game_versions:
                discord_user = bot.get_user(user.discord_id) or await bot.fetch_user(user.discord_id)
                if int(user.discord_id) == int(DISCORD_ADMIN_ID):
                    print("\n[notify_about_updates] Is admin user\n")
                    discord_channel = bot.get_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID)) \
                        or await bot.fetch_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID))
                else:
                    discord_channel = None
                result = f'Found {len(game_versions)} new updates:\n'
                for game, game_version in game_versions:
                    result += f'{game.name}, Latest Version: {game_version.version}, ' \
                              f'Last Updated At: <t:{int(datetime.datetime.timestamp(game_version.published_at))}:f> <{game.url}> | <{game_version.devlog}>\n'
                    if len(result) > 1600:
                        await discord_user.send(result)
                        if discord_channel:
                            await discord_channel.send(result)
                        result = ''
                if result:
                    await discord_user.send(result)
                    if discord_channel:
                        await discord_channel.send(result)
                user.processed_at = start_time
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


@bot.slash_command(name="search")
async def search(ctx, name):
    if name:
        await ctx.defer()
        with Session() as session:
            games = session.query(Game, GameVersion) \
                .join(GameVersion, GameVersion.game_id == Game.id) \
                .filter(
                    Game.is_visible == True,
                    Game.name.contains(name),
                    GameVersion.is_latest == True
                ) \
                .all()
            matches = len(games)
            if matches:
                result = f'Found {matches} matches for "{name}":\n'
                for game, version in games:
                    if len(result) > 1600:
                        await ctx.send(result.strip())
                        result = ''
                    result += f'{game.name}, Latest Version: {version.version}, ' \
                              f'Last Updated At: <t:{int(datetime.datetime.timestamp(version.published_at))}:f> <{game.url}>\n'
            else:
                result = f'Found no matches for "{name}"'
    else:
        result = 'Usage: <command> <search term>'
    await ctx.followup.send(result.strip())


bot.run(DISCORD_API_KEY)
