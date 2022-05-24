import logging

import disnake
from disnake.ext import commands

import log_analyzer

TOKEN = '<YOUR TOKEN>'

logger = logging.getLogger(__name__)

intents = disnake.Intents.default()
intents.message_content = True
bot = commands.InteractionBot(intents=intents)

analyzer = log_analyzer.LogAnalyzer(bot)


@bot.message_command(name="Analyze OBS Log", description="Analyzes Logs from OBS (does not work on SLD)")
async def context_menu_analyze(inter):
    target = inter.data.target
    channel = await bot.fetch_channel(target.channel.id)
    message = await channel.fetch_message(target.id)

    output_embed = await analyzer.parse_message(message)

    if output_embed is not None:
        await inter.response.send_message(embed=output_embed)
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

    output_embed = await analyzer.analyze_candidates()
    if output_embed is not None:
        await inter.response.send_message(embed=output_embed)
    else:
        await inter.response.send_message("Couldn't find anything to analyze")

print("Started Bot")
bot.run(TOKEN)
