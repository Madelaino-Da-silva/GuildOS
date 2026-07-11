"""
GuildOS Discord bot entrypoint.

Run standalone with:
    python -m app.discord_bot.bot

Or as the `bot` service in Docker Compose. Talks to the same database as
the FastAPI app (both are just Python processes sharing the DB URL), so
data submitted via Discord shows up on the dashboard immediately and vice
versa.
"""
from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("guildos.bot")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

INITIAL_EXTENSIONS = [
    "app.discord_bot.cogs.recruitment",
]


class GuildOSBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=settings.DISCORD_COMMAND_PREFIX, intents=INTENTS)

    async def setup_hook(self) -> None:
        for extension in INITIAL_EXTENSIONS:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

        guild = discord.Object(id=settings.DISCORD_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info("Synced %d slash command(s) to guild %s", len(synced), settings.DISCORD_GUILD_ID)

    async def on_ready(self) -> None:
        logger.info("GuildOS bot logged in as %s (id=%s)", self.user, self.user.id if self.user else "?")


def main() -> None:
    bot = GuildOSBot()
    bot.run(settings.DISCORD_BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
