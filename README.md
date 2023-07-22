# itchbot

## What does it do?

This project fetches metadata from itch.io, serves the processed data on a website, and makes it accessible via a Discord bot interface.

There are 3 major components:

### Update Component:

The data is fetched for each entry of a single configured collection.
The data of each item on that watchlist includes information such as:
- Name
- URL
- Tags
- Average rating
- Latest version

This data is stored within a MySQL database for use in the other two components.

### Web Component:

This component serves a simple browse-, search-, and sorteable web view of the data fetched by the Update Companent.
A live sample of that view can be seen at https://akiba.games

### Discord Bot Component:

An invite of the bot to a Discord server can be triggered at <your_server_address>/discord/
Live example: https://akiba.games/discord/ (Currently completely unstyled)

Once invited, the bot offers several commands:

* !subscribe - Subscribe to receive private messages whenever an update has been found
* !unsubscribe - Unsubscribe from the private message
* !refresh - Refresh all game metadata
* !search - Search for a particular pattern, and return all matches with update information

## How Do I Run It?

### Option 1: Docker

A docker setup for the project can be found at at https://github.com/Rejaku/itchbot-docker  
Follow the README in the docker project for setup instructions.

### Option 2: Self-managed

Expected environment:
* Unix-like system
* MariaDB ~10.10
* Python ~3.11
* Any web server (nginx, Apache2, ...) as reverse proxy endpoint for SSL termination

To function properly, a number of environment variables are expected to be set before application start:
* DB - name of the DB
* DB_USER - DB user with read & write permissions to DB
* DB_PASSWORD
* ITCH_API_KEY - Your itch.io API key. It can be got at https://itch.io/user/settings/api-keys
* ITCH_COLLECTION_ID - The ID of the collection to use for all other processes. This is corrently a single collection, that can not be managed via any interface.
* DISCORD_API_KEY - Discord API information can be found at https://discord.com/developers/applications  
Note: The bot requires "Message Content Intent" permission to function
* DISCORD_CLIENT_ID
* DISCORD_CLIENT_SECRET
* DISCORD_REDIRECT_URI=https://<your_domain>/callback
* FLASK_SECRET - Randomly generated string to use as internal secret

Starting the application:
```
git clone https://github.com/Rejaku/itchbot.git
cd itchbot
python3 -m pip install --user virtualenv
python3 -m venv venv
source venv/bin/activate
python3 -m pip install install -r requirements.txt
# Start the Discord bot, detached
python3 main.py &
# Start the updater & web service, detached
python3 web.py &
```

Once up and running, you can invite the bot to your server by going to https://<your_domain>/discord and click on the option "Invite Bot with permissions 3072 (Read & Send Messages)"  
When joined, it will react to the bot commands, and respond within the channel the command was triggered in. User can also subscribe and unsubscribe to individual notifications by interacting with the bot.

