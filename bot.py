# Michael Peters

import secrets
import discord
import asyncio
import requests
import sqlite3
import shortuuid
import toml
from discord.ext import commands, tasks

secrets_file = "data/secrets.toml"
secrets = toml.load(secrets_file)

bot = commands.Bot(command_prefix="z-", description="zombieland")
conn = sqlite3.connect("data/issues.sqlite3")
c = conn.cursor()

DEBUG = False  # debug printer

create_table_stmt = "CREATE TABLE IF NOT EXISTS issues (id TEXT, description TEXT, name TEXT, status INTEGER)"

c.execute(create_table_stmt)


def debugPrint(text, val):
    if val:
        print(text)


@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))
    bot.loop.create_task(get_battlemetrics_server(secrets["discord"]["server"]))


def is_me(m):
    return m.author == bot.user


def is_command(m):
    return m.content.startswith("z-")


@bot.command(pass_context=True)
async def clearissues(ctx):
    channel = bot.get_channel(secrets["discord"]["issue_channel_id"])
    deleted = await channel.purge(limit=100)
    await channel.send("❌ Deleted {} message(s)".format(len(deleted)))


@bot.command(pass_context=True)
async def clear(ctx):
    channel = ctx.message.channel
    deleted = await channel.purge(limit=100, check=is_me)
    deleted2 = await channel.purge(limit=100, check=is_command)
    await channel.send("❌ Deleted {} message(s)".format(len(deleted + deleted2)))


async def get_battlemetrics_server(server):
    while True:
        r = requests.get("https://api.battlemetrics.com/servers/%s" % server)
        if r != None:
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
                    activity=discord.Game(name=offline_game_name),
                    status=discord.Status.dnd,
                )
            await asyncio.sleep(60)  # run coroutine every 60 seconds
        else:
            await asyncio.sleep(60)


@bot.command(pass_context=True)
async def players(ctx):
    players_url = "https://api.battlemetrics.com/players?filter%5Bservers%5D=7182527&page%5Bsize%5D=50&filter%5Bonline%5D=true"
    players = requests.get(players_url)
    if players != None:
        players_json = players.json()
        channel = ctx.message.channel
        str = ""

        embed = discord.Embed(title="Zombieland Rust", color=0x00A13E)
        for player in players_json["data"]:
            debugPrint(player["attributes"]["name"], DEBUG)
            str = str + player["attributes"]["name"] + "\n"

        embed.add_field(name="Players:", value=str, inline=True)
        embed.set_footer(text="Thanks for playing.")
        await channel.send(embed=embed)


@bot.command(pass_context=True)
async def issue(ctx, *args):
    if not args:
        await ctx.message.channel.send("🛑 Please include a desciption")
    else:
        channel = bot.get_channel(secrets["discord"]["issue_channel_id"])
        name = "submitted by {}".format(ctx.message.author)
        description = " ".join(args)
        id = shortuuid.uuid()

        data = (id, description, "{}".format(ctx.message.author), 0)
        c.execute("INSERT INTO issues VALUES (?,?,?,?)", data)

        embed = discord.Embed(
            title="🛑 Issue Report 🛑", description=name, color=0xAD0303
        )
        embed.add_field(name="issue ID", value=id, inline=False)
        embed.add_field(name="description", value=description, inline=False)
        embed.set_footer(text="an admin will be with you shortly.")
        conn.commit()
        await ctx.message.channel.send(
            "✅ Thanks for submitting. Check %s for more information" % channel.mention
        )
        await channel.send(
            "Attention %s: New Issue Report " % secrets["discord"]["admin_role_string"]
        )
        new_issue = await channel.send(embed=embed)
        # await new_issue.add_reaction("✅")


@bot.command(pass_context=True)
async def open(ctx):
    channel = bot.get_channel(secrets["discord"]["issue_channel_id"])
    author = ctx.message.author
    if secrets["discord"]["admin_role_id"] in [y.id for y in author.roles]:
        if c.execute("SELECT * FROM issues WHERE status = 0").fetchone() != None:
            for row in c.execute("SELECT * FROM issues WHERE status = 0"):
                name = "submitted by {}".format(row[2])
                embed = discord.Embed(
                    title="🛑 Issue Report 🛑", description=name, color=0xAD0303
                )
                embed.add_field(name="issue ID", value=row[0], inline=False)
                embed.add_field(name="description", value=row[1], inline=False)
                embed.set_footer(text="an admin will be with you shortly.")

                await channel.send(embed=embed)
        else:
            await channel.send("No open issues at this time ✅")


@bot.command(pass_context=True)
async def resolve(ctx, arg1, *args):
    author = ctx.message.author
    c.execute("SELECT * FROM issues WHERE status = 0")
    result = c.fetchone()
    data = (arg1,)
    if result != None:
        if not args:
            await ctx.message.channel.send("🛑 Please include a desciption")
        else:
            if secrets["discord"]["admin_role_id"] in [y.id for y in author.roles]:
                description = " ".join(args)
                c.execute("UPDATE issues SET status = 1 WHERE id = (?)", data)
                conn.commit()

                name = "resolved by {}".format(author)
                channel = bot.get_channel(secrets["discord"]["issue_channel_id"])
                embed = discord.Embed(
                    title="✅ Issue Resolved ✅", description=name, color=0x00A13E
                )
                embed.add_field(name="issue ID", value=result[0], inline=False)
                embed.add_field(name="description", value=description, inline=False)
                embed.set_footer(text="Thanks for your report.")

                await channel.send(embed=embed)


bot.run(secrets["key"]["token"])
