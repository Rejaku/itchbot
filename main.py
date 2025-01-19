# This bot requires the 'message_content' privileged intent to function.
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

    def build_updates_message(updates):
        result = f'Found {len(updates)} new updates:\n'
        update_message_chunks = []

        for game in updates:
            update_text = (
                f'{game["name"]}, Latest Version: {game["version"]}, '
                f'Last Updated At: <t:{game["published_at"]}:f> '
                f'<{game["url"]}> | <{game["devlog"]}>\n'
            )

            if len(result) + len(update_text) > 1600:
                update_message_chunks.append(result)
                result = update_text
            else:
                result += update_text

        if result:
            update_message_chunks.append(result)

        return update_message_chunks

    try:
        response = requests.post(
            f'{LARAVEL_API_URL}/api/discord/updates',
            headers=api_headers(),
        )
        response.raise_for_status()
        data = response.json()

        if data['updates']:
            message_chunks = build_updates_message(data['updates'])

            # Send DMs to all subscribed users
            for discord_id in data['discord_users']:
                try:
                    # Get Discord user object
                    discord_user = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                    if not discord_user:
                        continue

                    for chunk in message_chunks:
                        await discord_user.send(chunk)

                except Exception as e:
                    print(f"Error sending notification to user {discord_id}: {str(e)}")
                    continue

            # If updates were found and admin user is in the list, send to notification channel
            if DISCORD_NOTIFICATIONS_CHANNEL_ID and DISCORD_ADMIN_ID in data['discord_users']:
                try:
                    discord_channel = bot.get_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID)) \
                                      or await bot.fetch_channel(int(DISCORD_NOTIFICATIONS_CHANNEL_ID))
                    if discord_channel:
                        for chunk in message_chunks:
                            await discord_channel.send(chunk)
                except Exception as e:
                    print(f"Error sending to notification channel: {str(e)}")

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