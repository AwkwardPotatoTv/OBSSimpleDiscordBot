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
bot = commands.InteractionBot(intents=intents, test_guilds=[744333418724065370])

analyzer = log_analyzer.LogAnalyzer(bot)


@bot.message_command(name="Analyze OBS Log", description="Analyzes Logs from OBS (does not work on SLD)")
async def context_menu_analyze(inter):
    target = inter.data.target
    channel = await bot.fetch_channel(target.channel.id)
    message = await channel.fetch_message(target.id)

    output_embed, action_row = await analyzer.parse_message(message)

    if output_embed is not None:
        await inter.response.send_message(embed=output_embed, components=action_row)
    else:
        await inter.response.send_message("Couldn't find anything to analyze")


@bot.slash_command(description="Analyzes Logs from OBS (does not work on SLD)")
async def analyze_log(inter, link: str = None, attachment: disnake.Attachment = None):
    if link is not None:
        await analyzer.add_candidate(link)
    elif attachment is not None:
        await analyzer.add_candidate(attachment)
    else:
        return await inter.response.send_message("Please attach some kind of log", hidden=True)

    output_embed, action_row = await analyzer.analyze_candidates()
    if output_embed is not None:
        await inter.response.send_message(embed=output_embed, components=action_row)
    else:
        await inter.response.send_message("Couldn't find anything to analyze")

logging.info("--- Started Bot ---")
bot.run(TOKEN)
