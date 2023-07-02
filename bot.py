import discord
from discord import Intents, app_commands
from discord.ext import tasks, commands
import discord_user_data
from user_performance import performance_analysis
import os
import requests
from datetime import datetime, time, date
import pytz
from replit import db
import math

intents = Intents.default()
intents.message_content = True
prefix = "!lb"
bot = commands.Bot(command_prefix=prefix, intents=intents)
wua_waiting = False
last_message_ids = ()  # author, message


async def send_streak_holders(interaction, user_info):
    async with interaction.channel.typing():
        data = convert_observed_dict_to_dict(db["streak"])
        lm_user = list(data["LM"].keys())[0]
        wu_user = list(data["WU"].keys())[0]
        lm_streak = data["LM"][str(lm_user)]
        wu_streak = data["WU"][str(wu_user)]
        eb = discord.Embed(title="**Current Streak Holders**",
                           color=discord.Color.from_rgb(255, 88, 62),
                           url="https://en.wikipedia.org/wiki/Among_Us",
                           timestamp=datetime.utcnow())
        eb.add_field(
            name="Waking Up Award",
            value=f"<@{int(wu_user)}> with **{wu_streak}**🔥",
            inline=False)
        eb.add_field(
            name="Last Message Of The Day",
            value=f"<@{int(lm_user)}> with **{lm_streak}**🔥",
            inline=False)
        eb.set_footer(text=user_info[0], icon_url=user_info[1])
        eb.set_thumbnail(url=user_info[2])
        return eb


def convert_observed_dict_to_dict(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, "value"):
        return convert_observed_dict_to_dict(data.value)
    else:
        return data


def convert_observed_list_to_list(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, "value"):
        if isinstance(data.value, list):
            return [convert_observed_dict_to_dict(item) for item in data.value]
        elif isinstance(data.value, tuple):
            return tuple(convert_observed_dict_to_dict(item) for item in data.value)
    else:
        return data


def update_streak(lm, winner_id):
    data = convert_observed_dict_to_dict(db["streak"])
    if lm:
        if list(data["LM"].keys())[0] == str(winner_id):
            data["LM"][str(winner_id)] += 1
        else:
            data["LM"] = {str(winner_id): 1}
    else:
        if list(data["WU"].keys())[0] == str(winner_id):
            data["WU"][str(winner_id)] += 1
        else:
            data["WU"] = {str(winner_id): 1}

    db["streak"] = data
    if lm:
        return data["LM"][str(winner_id)]
    else:
        return data["WU"][str(winner_id)]


async def award_win(award, db_key, winner_id, channel, lm, interaction):
    data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db[db_key])))
    current_date = date.today()
    formatted_date = current_date.strftime("%Y-%m-%d")
    if str(winner_id) not in data:
        data[str(winner_id)] = ([formatted_date], 1)
    else:
        data[str(winner_id)][0].append(formatted_date)
        data[str(winner_id)][1] += 1
    db[db_key] = data
    if lm:
        db["LM_by_date"][formatted_date] = winner_id
    else:
        db["WU_by_date"][formatted_date] = winner_id
    streak = update_streak(lm, winner_id)
    winner = f"<@{winner_id}>"
    message = f"{winner} has now won the {award} Award **{data[str(winner_id)][1]}** times.     **{streak}**🔥"
    if channel is None:
        interaction.response.send_message(message)
    else:
        await channel.send(message)


@tasks.loop(seconds=1)
async def find_LM_winner():
    uk_timezone = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_timezone).time()
    target_time = time(hour=0, minute=0, second=0)
    if current_time.hour == target_time.hour and current_time.minute == target_time.minute and current_time.second == target_time.second:
        global last_message_ids
        message_id = last_message_ids[1]
        user_id = last_message_ids[0]
        channel = bot.get_channel(525730239800672257)  # g e n e r a l 525730239800672257
        message = await channel.fetch_message(message_id)
        await message.add_reaction("🏆")
        award = "Last Message Of The Day"
        await award_win(award, "LM_scores", user_id, channel, True, None)


def leaderboard_embed(title, db_key, user_info):
    data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db[db_key])))
    leaders = sorted(data.items(), key=lambda x: x[1][1], reverse=True)
    eb = discord.Embed(title=f"**{title}**",
                       color=discord.Color.from_rgb(255, 88, 62),
                       url="https://en.wikipedia.org/wiki/Among_Us",
                       timestamp=datetime.utcnow())
    for i in range(min(10, len(leaders))):
        position = str(int(i + 1))
        if position == "1":
            position = "1st 🥇"
        elif position == "2":
            position = "2nd 🥈"
        elif position == "3":
            position = "3rd 🥉"
        else:
            position = position + "th"
        eb.add_field(
            name=f"{position}",
            value=f"<@{int(leaders[i][0])}> with **{leaders[i][1][1]}** wins", inline=False)
    eb.set_footer(text=user_info[0], icon_url=user_info[1])
    eb.set_thumbnail(url=user_info[2])
    return eb


async def send_leaderboard(title, db_key, message, user_info):
    async with message.channel.typing():
        eb = leaderboard_embed(title, db_key, user_info)
        options = [
            discord.SelectOption(label="Waking Up Early Award Leaderboard", value="1", emoji="🌇", default=True),
            discord.SelectOption(label="Last Message Of The Day Leaderboard", value="2", emoji="🌃", default=False)
        ]

        select = discord.ui.Select(
            placeholder="🌇 Waking Up Early Award Leaderboard 🌇",
            options=options,
            custom_id="select_menu",
        )

        view = discord.ui.View()
        view.add_item(select)
        return eb, view


async def send_stats(message, user_info, users_list, db_key, graph_title):
    async with message.channel.typing():
        file = performance_analysis.all_users_win_rate_graph(users_list, db_key, graph_title)
        eb = discord.Embed(title="**Performance Comparison**",
                           color=discord.Color.from_rgb(255, 88, 62),
                           url="https://en.wikipedia.org/wiki/Among_Us",
                           timestamp=datetime.utcnow())
        eb.set_image(url="attachment://graphs.png")
        eb.set_footer(text=user_info[0], icon_url=user_info[1])
        eb.set_thumbnail(url=user_info[2])
        await message.channel.send(file=file, embed=eb)


async def send_user_analysis(user_id, user_info, message):
    async with message.channel.typing():
        lm_wins_data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db["LM_scores"])))
        wu_wins_data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db["WU_scores"])))
        try:
            lm_wins = lm_wins_data[user_id][1]
        except KeyError:
            lm_wins = 0
        try:
            wu_wins = wu_wins_data[user_id][1]
        except KeyError:
            wu_wins = 0
        lm_win_rate = performance_analysis.find_user_win_rate_lm(user_id)
        wu_win_rate = performance_analysis.find_user_win_rate_wu(user_id)
        username = discord_user_data.get_user_info(user_id)["username"]
        eb = discord.Embed(title=f"**Performance Analysis for {username}**",
                           color=discord.Color.from_rgb(255, 88, 62),
                           url="https://en.wikipedia.org/wiki/Among_Us",
                           timestamp=datetime.utcnow())
        eb.add_field(
            name=f"Waking Up Early Award - {wu_wins} wins",
            value=f"Current win rate: **{round_to_3sf(wu_win_rate * 100)}%**", inline=False)
        eb.add_field(
            name=f"Last Message Of The Day Award - {lm_wins} wins",
            value=f"Current win rate: **{round_to_3sf(lm_win_rate * 100)}%**", inline=False)
        file = performance_analysis.user_performance_graphs(user_id)
        eb.set_image(url="attachment://graphs.png")
        eb.set_footer(text=user_info[0], icon_url=user_info[1])
        eb.set_thumbnail(url=discord_user_data.get_user_info(user_id)["profile_picture"])
        return file, eb


def round_to_3sf(number):
    try:
        rounded_number = round(number, -int(math.floor(math.log10(abs(number)))) + 2)
    except ValueError:
        rounded_number = 0
    formatted_number = '{:g}'.format(rounded_number)
    return formatted_number


@bot.event
async def on_interaction(interaction):
    if isinstance(interaction, discord.Interaction):
        try:
            interaction.data["custom_id"] == "select_menu"
        except KeyError:
            return
        interaction_user_info = discord_user_data.get_user_info(interaction.user.id)
        bot_user_info = discord_user_data.get_user_info(895026694757445694)
        user_info = [interaction_user_info["username"],
                     interaction_user_info["profile_picture"],
                     bot_user_info["profile_picture"]]
        selected_option = interaction.data["values"][0]
        if selected_option == "1":
            embed = leaderboard_embed("🌇 Waking Up Early Award Leaderboard 🌇", "WU_scores", user_info)
            placeholder = "🌇 Waking Up Early Award Leaderboard 🌇"
        elif selected_option == "2":
            embed = leaderboard_embed("🌃 Last Message Of The Day Leaderboard 🌃", "LM_scores", user_info)
            placeholder = "🌃 Last Message Of The Day Leaderboard 🌃"
        else:
            embed = leaderboard_embed("🌇 Waking Up Early Award Leaderboard 🌇", "WU_scores", user_info)
            placeholder = "🌇 Waking Up Early Award Leaderboard 🌇"

        select = discord.ui.Select(
            placeholder=placeholder,
            options=[
                discord.SelectOption(label="Waking Up Early Award Leaderboard", value="1", emoji="🌇",
                                     default=selected_option == "1"),
                discord.SelectOption(label="Last Message Of The Day Leaderboard", value="2", emoji="🌃",
                                     default=selected_option == "2")
            ],
            custom_id="select_menu",
        )

        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(embed=embed, view=view)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="#g-e-n-e-r-a-l"))


@bot.tree.command(name='sync', description='Owner only', guild=discord.Object(id=878982626306826271))
async def sync(interaction: discord.Interaction):
    if interaction.user.id == 603142766805123082:
        await bot.tree.sync()
        await interaction.response.send_message('Command tree synced')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')


@bot.tree.command(name="leaderboard", description="Get leaderboard")
async def cmd_lb(interaction: discord.Interaction):
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    embed, view = await send_leaderboard("🌇 Waking Up Early Award Leaderboard 🌇", "WU_scores", interaction, user_info)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="streaks", description="Get current streak holders")
async def cmd_streaks(interaction: discord.Interaction):
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    embed = await send_streak_holders(interaction, user_info)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userstats", description="Get user performance")
async def cmd_user_stats(interaction: discord.Interaction, user: discord.Member):
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    file, embed = await send_user_analysis(str(user.id), user_info, interaction)
    await interaction.response.send_message(file=file, embed=embed)


@bot.tree.command(name="cmp", description="Compare performance between users")
@app_commands.choices(award=[
    app_commands.Choice(name="Waking Up Early Award", value="wu"),
    app_commands.Choice(name="Last Message Of The Day", value="lm")
])
async def cmd_cmp(interaction: discord.Interaction, award: app_commands.Choice[str], users: discord.Member):
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    await interaction.response.send_message("inactive command")
    # if award.value == "wu":
    #    return
    # await send_stats(interaction.message, user_info, users_list, "WU_by_date", "Waking Up Early Award Comparison")
    # else:
    #   return
    # await send_stats(interaction.message, user_info, users_list, "LM_by_date", "Last Message Of The Day Comparison")


@bot.tree.command(name="award", description="Award a win to a user")
@app_commands.choices(award=[
    app_commands.Choice(name="Waking Up Early Award", value="wu"),
    app_commands.Choice(name="Last Message Of The Day", value="lm")
])
async def cmd_award(interaction: discord.Interaction, award: app_commands.Choice[str], user: discord.Member):
    moderator_ids = [603142766805123082, 299216822647914499]
    if interaction.user.id not in moderator_ids:
        api_key = os.getenv("GIPHY")
        response = requests.get(f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=clown")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "url" in data["data"]:
                gif_url = data["data"]["url"]
                await interaction.response.send_message(gif_url)
            else:
                await interaction.response.send_message("dont be naughty!")
        else:
            await interaction.response.send_message("dont be naughty!")
        return
    if award.value == "wu":
        db_key = "WU_scores"
        lm = False
    else:
        db_key = "LM_scores"
        lm = True
    await award_win(award.name, db_key, user.id, None, lm, interaction)


@bot.event
async def on_message(message):
    global wua_waiting
    global last_message_ids
    if message.channel.id == 525730239800672257:  # 525730239800672257:
        last_message_ids = (message.author.id, message.id)
    if message.author.id == 696828737248952331:
        await message.add_reaction("❤️")
    if message.author.id == bot.user.id:
        return
    if not wua_waiting and message.author.id == 748488791471161405:  # WU bot id: 748488791471161405
        wua_waiting = True
    if wua_waiting and message.author.id != 748488791471161405 and message.channel.id == 525730239800672257:
        wua_waiting = False
        await message.add_reaction("🏆")
        winner_id = message.author.id
        award = "Waking Up Early"
        await award_win(award, "WU_scores", winner_id, message.channel, False, None)


bot.run(os.getenv("TOKEN"))
