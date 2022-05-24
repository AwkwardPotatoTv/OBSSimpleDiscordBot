# OBSSimpleDiscordBot

Simple log analyzer for OBS logs, extracted from the [OBS Bot](https://github.com/obsproject/obs-bot)

Analysis isn't automatic by default, trigger with the slash commands or context menu

# Usage: 

right click > apps > analyze obs log 

/analyze_log [link] [file] 

Optionally with a start flag, the bot can automatically scan new messages for logs

# Installation
1. `docker pull awkwardpotato/obs-log-bot`
2. Create a discord bot account
3. `docker run -d -e TOKEN=<BOT TOKEN> awkwardpotato/obs-log-bot` - optionally you can add `-e SCAN-MSG=True` to check for logs automatically

# Creating Discord Bot
1. Create new application at https://discord.com/developers/applications
2. Create bot (Under the bot tab)
3. Check `Message Content Intent` 
4. Copy/Save the generated token for later
5. Under OAUTH2 > Url Generator select `bot` and `applications.commands`
6. Under bot permissions select `send messages` and `read messages`
7. Copy the generated link > paste it into your browser > add to your server
