import logging

from asyncio import TimeoutError
from urllib.parse import parse_qs, urlparse, quote_plus as urlencode

import aiohttp
import disnake
from aiohttp import ClientResponseError
from disnake import Message, Embed, Colour
from disnake.enums import ButtonStyle
from disnake.ui.action_row import ActionRow

logger = logging.getLogger(__name__)


class LogAnalyzer:
    _analysis_colour = 0x5A7474
    _potato = '🥔'
    _log_download_failed = '❗️'
    _log_analyser_failed = '❌'

    _filtered_log_needles = ('obs-streamelements.dll', 'ftl_stream_create')
    _log_hosts = (
        'https://obsproject.com/logs/',
        'https://hastebin.com/',
        'https://pastebin.com/',
        'https://obsproject.com/tools/analyzer',
    )

    def __init__(self, bot):
        self.bot = bot
        self.log_candidates = []
        self.msg = None

    async def parse_message(self, msg: Message):
        self.msg = msg
        # check if messaage has possible log urls, or an attachment
        if not msg.attachments and not any(lh in msg.content for lh in self._log_hosts):
            return

        # list of candidate tuples consisting of (raw_url, web_url)
        # message attachments
        for attachment in msg.attachments:
            if attachment.url.endswith('.txt'):
                # collisions are possible here, but unlikely, we'll see if it becomes a problem
                self.log_candidates.append(attachment.url)

        # links in message
        for part in [p.strip() for p in msg.content.split()]:
            if any(part.startswith(lh) for lh in self._log_hosts):
                if 'obsproject.com/logs/' in part:
                    url = part
                elif 'obsproject.com/tools/analyzer' in part:
                    parsed = urlparse(part)
                    if log_url := parse_qs(parsed.query).get('log_url', [None])[0]:
                        url = log_url
                elif 'hastebin.com' in part:
                    hastebin_id = part.rsplit('/', 1)[1]
                    if not hastebin_id:
                        continue
                    url = f'https://hastebin.com/raw/{hastebin_id}'
                elif 'pastebin.com' in part:
                    pastebin_id = part.rsplit('/', 1)[1]
                    if not pastebin_id:
                        continue
                    url = f'https://pastebin.com/raw/{pastebin_id}'
                else:
                    continue

                self.log_candidates.append(url)

        if not self.log_candidates:
            return

        if len(self.log_candidates) > 3:
            logger.debug('Too many log url candidates, limiting to first 3')
            self.log_candidates = self.log_candidates[:3]

        return await self.analyze_candidates()

    async def add_candidate(self, candidate):
        if isinstance(candidate, disnake.Attachment):
            logger.info(candidate.url)
            self.log_candidates.append(candidate.url)
        else:
            self.log_candidates.append(candidate)

    async def analyze_candidates(self):
        for log_url in self.log_candidates:
            # download log for local analysis
            try:
                log_content = await self._download_log(log_url)
                break
            except ValueError:  # not a valid OBS log
                continue
            except (ClientResponseError, TimeoutError):  # file download failed
                logger.error(f'Failed retrieving log from "{log_url}"')
                await self.react(self._log_download_failed)
            except Exception as e:  # catch everything else
                logger.error(f'Unhandled exception when downloading log: {repr(e)}')
        else:
            return

        log_analysis = None
        try:
            # fetch log analysis from OBS analyser
            log_analysis = await self._fetch_log_analysis(log_url)
        except ValueError:
            logger.error(f'Analyser result for "{log_url}" is invalid.')
        except ClientResponseError:  # file download failed
            logger.error(f'Failed retrieving log analysis from "{log_url}"')
        except TimeoutError:  # analyser failed to respond
            logger.error(f'Analyser timed out for log file "{log_url}"')
        except Exception as e:  # catch everything else
            logger.error(f'Unhandled exception when analysing log: {repr(e)}')
        finally:
            if not log_analysis:
                return await self.react(self._log_analyser_failed)

        anal_url = f'https://obsproject.com/tools/analyzer?log_url={urlencode(log_url)}'
        embed = Embed(colour=Colour(0x5A7474), url=anal_url)

        def pretty_print_messages(msgs):
            ret = []
            for _msg in msgs:
                ret.append(f'- {_msg}')
            return '\n'.join(ret)

        if log_analysis['critical']:
            embed.add_field(name="🛑 Critical", value=pretty_print_messages(log_analysis['critical']))
        if log_analysis['warning']:
            embed.add_field(name="⚠️ Warning", value=pretty_print_messages(log_analysis['warning']))
        if log_analysis['info']:
            embed.add_field(name="ℹ️ Info", value=pretty_print_messages(log_analysis['info']))

        # include filtered log in case SE or FTL spam is detected
        if 'obsproject.com' in log_url and any(elem in log_content for elem in self._filtered_log_needles):
            clean_url = log_url.replace('obsproject.com', 'obsbot.rodney.io')
            embed.description = (
                f'*Log contains debug messages (browser/ftl/etc), '
                f'for a filtered version [click here]({clean_url})*\n'
            )

        # Clear log candidates
        self.log_candidates = []

        row = ActionRow()
        row.add_button(style=ButtonStyle.link, label='Solutions / Full Analysis', url=anal_url)
        return embed, row

    async def _fetch_log_analysis(self, url):
        async with aiohttp.ClientSession() as session:
            r = await session.get(
                'https://obsproject.com/analyzer-api/', params=dict(url=url, format='json')
            )
            if r.status == 200:
                j = await r.json()
                # check if analysis response is actually valid
                if not all(i in j for i in ('critical', 'warning', 'info')):
                    raise ValueError('Analyser result invalid')

                return j
            else:
                r.raise_for_status()

    async def _download_log(self, url):
        async with aiohttp.ClientSession() as session:
            r = await session.get(url)
            if r.status == 200:
                try:
                    log = await r.text()
                except UnicodeDecodeError:
                    logger.warning('Decoding log failed, trying with ISO-8859-1 encoding forced...')
                    log = await r.text(encoding='ISO-8859-1')

                if 'Stack' in log and 'EIP' in log or 'Anonymous UUID' in log or 'Fault address:' in log:
                    raise ValueError('Log is crash log')

                if 'log file uploaded at' not in log:  # uploaded within OBS
                    if 'Startup complete' not in log:  # not uploaded within OBS but still a log
                        raise ValueError('Not a (valid) OBS log')

                return log
            else:
                # Raise if status >= 400
                r.raise_for_status()

    async def react(self, emote):
        try:
            await self.msg.add_reaction(emote)
        except Exception as e:
            logger.warning(f'Adding reaction failed with "{repr(e)}')
