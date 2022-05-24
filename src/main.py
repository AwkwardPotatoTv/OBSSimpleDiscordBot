import logging
import os

import disnake
from disnake.ext import commands

import log_analyzer

TOKEN = os.environ['TOKEN']

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

intents = disnake.Intents.default()
intents.message_content = True
bot = commands.InteractionBot(intents=intents)

analyzer = log_analyzer.LogAnalyzer(bot)


@bot.message_command(name="Analyze OBS Log", description="Analyzes Logs from OBS (does not work on SLD)")
async def context_menu_analyze(inter):
    target = inter.data.target
    channel = await bot.fetch_channel(target.channel.id)
    message = await channel.fetch_message(target.id)

    try:
        output_embed, action_row = await analyzer.parse_message(message)
    except TypeError:
        return await inter.response.send_message("Couldn't find anything to analyze")

    await inter.response.send_message(embed=output_embed, components=action_row)


@bot.slash_command(description="Analyzes Logs from OBS (does not work on SLD)")
async def analyze_log(inter, link: str = None, attachment: disnake.Attachment = None):
    if link is not None:
        await analyzer.add_candidate(link)
    elif attachment is not None:
        await analyzer.add_candidate(attachment)
    else:
        return await inter.response.send_message("Please attach some kind of log")

    try:
        output_embed, action_row = await analyzer.analyze_candidates()
    except TypeError:
        return await inter.response.send_message('Failed to analyze log')

    await inter.response.send_message(embed=output_embed, components=action_row)


# Automatically scans all in-bound messages for an OBS log to analyze it, enabled at container start-up
scan_messages = os.getenv('SCAN-MSG', False)
if scan_messages is True:
    logger.info("[Enabled] - Scanning messages for OBS Logs")

    @bot.event
    async def on_message(message):
        # Returns if the analyzer could not find anything
        try:
            embed, action_row = await analyzer.parse_message(message)
        except TypeError:
            return

        await message.reply(embed=embed, components=action_row)
else:
    logger.info('[Disabled] - Log Analysis must be triggered manually')

logger.info("--- Started Bot ---")
bot.run(TOKEN)
