import discord
from discord import Intents, app_commands
from discord.ext import tasks, commands
import discord_user_data
from user_performance import performance_analysis
from keep_alive import keep_alive
import os
import requests
from datetime import datetime, time, date, timedelta
import pytz
from replit import db
import math
from PIL import Image
from io import BytesIO

intents = Intents.default()
intents.message_content = True
prefix = "!lb"
bot = commands.Bot(command_prefix=prefix, intents=intents)


async def send_streak_holders(interaction, user_info):
    async with interaction.channel.typing():
        data = convert_observed_dict_to_dict(db["streak"])
        lm_user = list(data["LM"].keys())[0]
        wu_user = list(data["WU"].keys())[0]
        lm_streak = data["LM"][str(lm_user)]
        wu_streak = data["WU"][str(wu_user)]
        embed = discord.Embed(title="**Current Streak Holders**",
                              color=discord.Color.from_rgb(255, 88, 62),
                              url="https://en.wikipedia.org/wiki/Among_Us",
                              timestamp=datetime.utcnow())
        embed.add_field(
            name="Waking Up Award",
            value=f"<@{int(wu_user)}> with **{wu_streak}**🔥",
            inline=False)
        embed.add_field(
            name="Last Message Of The Day",
            value=f"<@{int(lm_user)}> with **{lm_streak}**🔥",
            inline=False)
        embed.set_footer(text=user_info[0], icon_url=user_info[1])
        embed.set_thumbnail(url=user_info[2])
        return embed


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


async def award_win(award, db_key, author, channel, lm, time_str, interaction):
    data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db[db_key])))
    current_date = date.today()
    formatted_date = current_date.strftime("%Y-%m-%d")
    winner_id = author.id
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
    if lm and time_str is not None:
        message = f"{author.mention} has now won the {award} Award **{data[str(winner_id)][1]}** times - {time_str}     **{streak}**🔥"
    else:
        message = f"{author.mention} has now won the {award} Award **{data[str(winner_id)][1]}** times.     **{streak}**🔥"
    if channel is None:
        await interaction.response.send_message(message)
    else:
        await channel.send(message)


@tasks.loop(seconds=1)
async def find_LM_winner():
    uk_timezone = pytz.timezone('Europe/London')
    current_time = datetime.now(uk_timezone).time()
    target_time = time(hour=0, minute=0, second=0)
    if current_time.hour == target_time.hour and current_time.minute == target_time.minute and current_time.second == target_time.second:
        channel = bot.get_channel(525730239800672257)  # g e n e r a l 525730239800672257
        target_date = datetime.now(uk_timezone).date() - timedelta(days=1)
        async for message in channel.history(limit=None):
            message_created_at = message.created_at
            if ((message_created_at.astimezone(uk_timezone)).date()) == target_date:
                message_id = message.id
                author = message.author
                message_created_at = message.created_at
                message_created_at_uk = message_created_at.astimezone(uk_timezone)
                current_datetime_uk = datetime.now(uk_timezone)
                time_diff = current_datetime_uk.replace(hour=0, minute=0, second=0,
                                                        microsecond=0) - message_created_at_uk
                total_seconds = time_diff.total_seconds()
                if total_seconds < 60:
                    time_diff_str = f"{total_seconds} seconds"
                elif total_seconds < 3600:
                    minutes = int(total_seconds // 60)
                    seconds = int(total_seconds % 60)
                    time_diff_str = f"{minutes} minutes and {seconds} seconds"
                else:
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    time_diff_str = f"{hours} hours and {minutes} minutes"
                break
        time_str = f'with **{time_diff_str}** left to spare!'
        message = await channel.fetch_message(message_id)
        await message.add_reaction("🏆")
        award = "Last Message Of The Day"
        await award_win(award, "LM_scores", author, channel, True, time_str, None)


def leaderboard_embed(title, db_key, user_info):
    data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db[db_key])))
    leaders = sorted(data.items(), key=lambda x: x[1][1], reverse=True)
    embed = discord.Embed(title=f"**{title}**",
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
        embed.add_field(
            name=f"{position}",
            value=f"<@{int(leaders[i][0])}> with **{leaders[i][1][1]}** wins", inline=False)
    embed.set_footer(text=user_info[0], icon_url=user_info[1])
    embed.set_thumbnail(url=user_info[2])
    return embed


async def send_leaderboard(title, db_key, message, user_info):
    async with message.channel.typing():
        embed = leaderboard_embed(title, db_key, user_info)
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
        return embed, view


def get_half_image(url, is_left_half):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    width, height = img.size
    if is_left_half:
        return img.crop((0, 0, width // 2, height))
    else:
        return img.crop((width // 2, 0, width, height))


def resize_and_combine_images(left_url, right_url):
    left_half = get_half_image(left_url, True)
    right_half = get_half_image(right_url, False)

    if left_half.width > right_half.width:
        dimension = left_half.width
    else:
        dimension = right_half.width

    left_half = left_half.resize((dimension, 2 * dimension), Image.LANCZOS)
    right_half = right_half.resize((dimension, 2 * dimension), Image.LANCZOS)

    combined_width = left_half.width + right_half.width
    combined_height = 2 * left_half.width

    combined_img = Image.new('RGB', (combined_width, combined_height))
    combined_img.paste(left_half, (0, 0))
    combined_img.paste(right_half, (dimension, 0))
    print(combined_img.width, combined_img.height)
    return combined_img.copy()


async def send_stats(user_info, users_list, db_key, graph_title):
    file = performance_analysis.all_users_win_rate_graph(users_list, db_key, graph_title)
    embed = discord.Embed(title=f"**Performance Comparison for {users_list[0].name} and {users_list[1].name}**",
                          color=discord.Color.from_rgb(255, 88, 62),
                          url="https://en.wikipedia.org/wiki/Among_Us",
                          timestamp=datetime.utcnow())
    embed.set_image(url="attachment://graphs.png")
    embed.set_footer(text=user_info[0], icon_url=user_info[1])

    user1_pfp = discord_user_data.get_user_info(users_list[0].id)["profile_picture"]
    user2_pfp = discord_user_data.get_user_info(users_list[1].id)["profile_picture"]
    result_image = resize_and_combine_images(user1_pfp, user2_pfp)
    result_image.save(f"static/{users_list[0].id}{users_list[1].id}.png")

    embed.set_thumbnail(
        url=f"https://leaderboardbot.jamesmedley13.repl.co/static/{users_list[0].id}{users_list[1].id}.png")

    return file, embed


async def send_user_analysis(user_id, user_info):
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
    embed = discord.Embed(title=f"**Performance Analysis for {user_info[0]}**",
                          color=discord.Color.from_rgb(255, 88, 62),
                          url="https://en.wikipedia.org/wiki/Among_Us",
                          timestamp=datetime.utcnow())
    embed.add_field(
        name=f"Waking Up Early Award - {wu_wins} wins",
        value=f"Current win rate: **{round_to_3sf(wu_win_rate * 100)}%**", inline=False)
    embed.add_field(
        name=f"Last Message Of The Day Award - {lm_wins} wins",
        value=f"Current win rate: **{round_to_3sf(lm_win_rate * 100)}%**", inline=False)
    file = performance_analysis.user_performance_graphs(user_id)
    embed.set_image(url="attachment://graphs.png")
    embed.set_footer(text=user_info[0], icon_url=user_info[1])
    embed.set_thumbnail(url=user_info[1])
    return file, embed


async def is_first_message(message_id):
    channel = bot.get_channel(525730239800672257)
    found = False
    async for message in channel.history(limit=None):
        if found:
            return message.author.id == 748488791471161405
        elif message.id == message_id:
            found = True


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
    find_LM_winner.start()


@bot.tree.command(name='sync', description='Owner only', guild=discord.Object(id=878982626306826271))
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    if interaction.user.id == 603142766805123082:
        await bot.tree.sync()
        await interaction.followup.send('Command tree synced')
    else:
        await interaction.followup.send('You must be the owner to use this command!')


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
    await interaction.response.defer(ephemeral=False)
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    file, embed = await send_user_analysis(str(user.id), user_info)
    await interaction.followup.send(file=file, embed=embed)


@bot.tree.command(name="compare", description="Compare performance between users")
@app_commands.choices(award=[
    app_commands.Choice(name="Waking Up Early Award", value="wu"),
    app_commands.Choice(name="Last Message Of The Day", value="lm")
])
async def cmd_cmp(interaction: discord.Interaction, award: app_commands.Choice[str], user1: discord.Member,
                  user2: discord.Member):
    await interaction.response.defer(ephemeral=False)
    author_info = discord_user_data.get_user_info(interaction.user.id)
    bot_user_info = discord_user_data.get_user_info(895026694757445694)
    user_info = [author_info["username"],
                 author_info["profile_picture"],
                 bot_user_info["profile_picture"]]
    if award.value == "wu":
        db_key = "WU_by_date"
        title = "Waking Up Award Comparison"
    else:
        db_key = "LM_by_date"
        title = "Last Message Of The Day Comparison"
    file, embed = await send_stats(user_info, [user1, user2], db_key, title)
    await interaction.followup.send(file=file, embed=embed)


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
    award_str = award.name.replace(" Award", "")
    await award_win(award_str, db_key, user, None, lm, None, interaction)


@bot.event
async def on_message(message):
    if message.author.id == 696828737248952331:
        await message.add_reaction("❤️")
    if message.author.id == bot.user.id:
        return
    if await is_first_message(message.id):
        await message.add_reaction("🏆")
        award = "Waking Up Early"
        await award_win(award, "WU_scores", message.author, message.channel, False, None, None)


keep_alive()
bot.run(os.getenv("TOKEN"))
