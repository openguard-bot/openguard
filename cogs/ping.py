import datetime
import random
import socket
import time
import asyncio

import discord
from discord.ext import commands
import humanize  # type: ignore
import psutil

from lists import jokes
from database import get_redis, get_connection


class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.redis = None

    async def initialize(self):
        # Establish & warm a single Redis connection at startup
        self.redis = await get_redis()
        try:
            await self.redis.ping()
        except Exception:
            pass

    async def _sample_pg(self, samples: int = 3) -> float:
        connection = await get_connection()
        if not connection:
            return float('inf')
        
        latencies = []
        async with connection as conn:
            for _ in range(samples):
                start = time.perf_counter()
                await conn.fetchval("SELECT 1")
                latencies.append((time.perf_counter() - start) * 1000)
        return sum(latencies) / len(latencies)

    async def _sample_redis(self, samples: int = 3) -> float:
        if not self.redis:
            return float('inf')
            
        latencies = []
        for _ in range(samples):
            start = time.perf_counter()
            await self.redis.ping()
            latencies.append((time.perf_counter() - start) * 1000)
        return sum(latencies) / len(latencies)

    @commands.hybrid_command(
        name="ping", description="Responds with the bot's latency."
    )
    async def slash_ping(self, ctx: commands.Context) -> None:
        # Pick the joke first so it doesn't skew timings
        joke = random.choice(jokes)

        # 1) WebSocket latency (built-in, already an average)
        ws_latency = self.bot.latency * 1000  # ms

        # 2) RTT for sending & editing a message
        start = time.perf_counter()
        msg = await ctx.send(joke)
        end = time.perf_counter()
        rtt = (end - start) * 1000  # ms

        # 3) Postgres average over a few SELECT 1 calls
        pg_avg = await self._sample_pg()
        if pg_avg == float('inf'):
            pg_line = "Postgres: Unreachable"
        else:
            pg_line = f"Postgres latency (avg): {pg_avg:.2f}ms"

        # 4) Redis average over a few PINGs
        redis_avg = await self._sample_redis()
        if redis_avg == float('inf'):
            redis_line = "Redis: Unreachable"
        else:
            redis_line = f"Redis latency (avg): {redis_avg:.2f}ms"

        # 5) Shard info
        shard = ctx.guild.shard_id if ctx.guild else None

        uptime = humanize.naturaldelta(discord.utils.utcnow() - self.bot.launch_time)
        mem_usage = psutil.Process().memory_info().rss / 1024**2
        cpu = psutil.cpu_percent()
        hostname = socket.gethostname()

        # Build & edit in one go
        lines = [
            "Pong! 🏓",
            f"WS latency: {ws_latency:.2f}ms",
            f"RTT: {rtt:.2f}ms",
            pg_line,
            redis_line,
            "",  # Blank line for spacing
            f"Bot uptime: {uptime}",
            f"Bot RAM usage: {mem_usage:.2f} MB",
            f"System CPU usage: {cpu:.2f}%",
            "",  # Blank line for spacing
            f"Shard ID: {shard}",
            f"Hostname: {hostname}",
        ]
        await msg.edit(content="\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    cog = Ping(bot)
    await cog.initialize()  # warm Redis
    await bot.add_cog(cog)
