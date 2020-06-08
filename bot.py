# Michael Peters

import secrets
import discord
import asyncio
import requests
import sqlite3
import shortuuid
from discord.ext import commands, tasks

bot = commands.Bot(command_prefix="z-", description="zombieland")
conn = sqlite3.connect("db/issues.sqlite3")
c = conn.cursor()

DEBUG = True  # debug printer

create_table_stmt = "CREATE TABLE IF NOT EXISTS issues (id TEXT, description TEXT, name TEXT, status INTEGER)"

c.execute(create_table_stmt)


def debugPrint(text, val):
    if val:
        print(text)


@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))
    bot.loop.create_task(get_battlemetrics(secrets.server))


async def get_battlemetrics(server):
    while True:
        r = requests.get("https://api.battlemetrics.com/servers/%s" % server)
        json_data = r.json()
        current_players = json_data["data"]["attributes"]["players"]
        game_name = "%s/50 players online" % current_players
        offline_game_name = "server offline"

        if json_data["data"]["attributes"]["status"] == "online":
            debugPrint(game_name, DEBUG)
            await bot.change_presence(
                activity=discord.Game(name=game_name), status=discord.Status.dnd
            )
        else:
            debugPrint(offline_game_name, DEBUG)
            await bot.change_presence(
                activity=discord.Game(name=offline_game_name), status=discord.Status.dnd
            )
        await asyncio.sleep(60)  # run coroutine every 60 seconds


@bot.command(pass_context=True)
async def issue(ctx, *args):
    channel = bot.get_channel(secrets.issue_channel_id)
    name = "submitted by {}".format(ctx.message.author)
    description = " ".join(args)
    id = shortuuid.uuid()

    data = (id, description, "{}".format(ctx.message.author), 0)
    c.execute("INSERT INTO issues VALUES (?,?,?,?)", data)

    embed = discord.Embed(title="🛑 Issue Report 🛑", description=name, color=0xAD0303)
    embed.add_field(name="issue ID", value=id, inline=False)
    embed.add_field(name="description", value=description, inline=False)
    embed.set_footer(text="an admin will be with you shortly.")
    conn.commit()
    await channel.send("Attention %s: New Issue Report " % secrets.admin_role_id)
    await channel.send(embed=embed)


@bot.command(pass_context=True)
async def open(ctx):
    for row in c.execute("SELECT * FROM issues WHERE status = 0"):
        channel = bot.get_channel(secrets.issue_channel_id)
        embed = discord.Embed(
            title="🛑 Issue Report 🛑", description=row[2], color=0xAD0303
        )
        embed.add_field(name="issue ID", value=row[0], inline=False)
        embed.add_field(name="description", value=row[1], inline=False)
        embed.set_footer(text="an admin will be with you shortly.")

        await channel.send(embed=embed)


@bot.command(pass_context=True)
async def resolve(ctx, arg1, *args):
    description = " ".join(args)
    print(arg1)
    print(description)


bot.run(secrets.token)
