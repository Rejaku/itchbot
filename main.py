# This bot requires the 'message_content' privileged intent to function.
import datetime
import os
import requests
from discord.ext import commands, tasks

DISCORD_API_KEY = os.environ['DISCORD_API_KEY']
DISCORD_ADMIN_ID = os.environ['DISCORD_ADMIN_ID']
DISCORD_NOTIFICATIONS_CHANNEL_ID = os.environ['DISCORD_NOTIFICATIONS_CHANNEL_ID']
LARAVEL_API_URL = os.environ['LARAVEL_API_URL']
LARAVEL_API_TOKEN = os.environ['LARAVEL_API_TOKEN']

bot = commands.Bot()


def api_headers():
    return {
        'Authorization': f'Bearer {LARAVEL_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }


@bot.event
async def on_ready():
    print('Bot is ready')
    if not notify_about_updates.is_running():
        notify_about_updates.start()


@tasks.loop(minutes=30)
async def notify_about_updates():
    print("\n[notify_about_updates] Start\n")
    await bot.wait_until_ready()

    try:
        response = requests.post(
            f'{LARAVEL_API_URL}/api/discord/updates',
            headers=api_headers(),
            json={
                'discord_id': DISCORD_ADMIN_ID,
                'after': datetime.datetime.utcnow().isoformat()
            }
        )
        response.raise_for_status()
        data = response.json()

        if data['updates']:
            # Get Discord channel and user objects
            discord_user = bot.get_user(int(DISCORD_ADMIN_ID)) or await bot.fetch_user(int(DISCORD_ADMIN_ID))
            discord_channel = bot.get_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID)) \
                              or await bot.fetch_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID))

            result = f'Found {len(data["updates"])} new updates:\n'

            for game in data['updates']:
                update_text = (
                    f'{game["name"]}, Latest Version: {game["version"]}, '
                    f'Last Updated At: <t:{game["published_at"]}:f> '
                    f'<{game["url"]}> | <{game["devlog"]}>\n'
                )

                if len(result) + len(update_text) > 1600:
                    await discord_user.send(result)
                    if discord_channel:
                        await discord_channel.send(result)
                    result = update_text
                else:
                    result += update_text

            if result:
                await discord_user.send(result)
                if discord_channel:
                    await discord_channel.send(result)

    except Exception as e:
        print(f"Error in notify_about_updates: {str(e)}")


@bot.slash_command(name="subscribe")
async def subscribe(ctx):
    try:
        response = requests.post(
            f'{LARAVEL_API_URL}/api/discord/subscribe',
            headers=api_headers(),
            json={'discord_id': str(ctx.author.id)}
        )
        response.raise_for_status()
        data = response.json()
        await ctx.respond(data['message'])
    except Exception as e:
        await ctx.respond(f'Error: {str(e)}')


@bot.slash_command(name="unsubscribe")
async def unsubscribe(ctx):
    try:
        response = requests.post(
            f'{LARAVEL_API_URL}/api/discord/unsubscribe',
            headers=api_headers(),
            json={'discord_id': str(ctx.author.id)}
        )
        response.raise_for_status()
        data = response.json()
        await ctx.respond(data['message'])
    except Exception as e:
        await ctx.respond(f'Error: {str(e)}')


@bot.slash_command(name="search")
async def search(ctx, name):
    if not name:
        await ctx.respond('Usage: <command> <search term>')
        return

    await ctx.defer()

    try:
        response = requests.post(
            f'{LARAVEL_API_URL}/api/discord/search',
            headers=api_headers(),
            json={'name': name}
        )
        response.raise_for_status()
        data = response.json()

        if data['matches']:
            result = f'Found {data["matches"]} matches for "{name}":\n'
            for game in data['games']:
                update_text = (
                    f'{game["name"]}, Latest Version: {game["version"]}, '
                    f'Last Updated At: <t:{game["published_at"]}:f> '
                    f'<{game["url"]}>\n'
                )

                if len(result) + len(update_text) > 1600:
                    await ctx.send(result.strip())
                    result = update_text
                else:
                    result += update_text
        else:
            result = f'Found no matches for "{name}"'

        await ctx.followup.send(result.strip())
    except Exception as e:
        await ctx.followup.send(f'Error: {str(e)}')


bot.run(DISCORD_API_KEY)