import json
import discord
from datetime import datetime
from replit import db
import matplotlib.pyplot as plt
import io
from PIL import Image


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


def find_user_win_rate_lm(user_id):  # total win rate
    lm_by_date = db["LM_by_date"]
    total_wins_count = len(lm_by_date.keys())
    win_data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db["LM_scores"])))
    try:
        user_win_count = win_data[str(user_id)][1]
    except KeyError:
        user_win_count = 0
    return user_win_count / total_wins_count


def find_user_win_rate_wu(user_id):  # total win rate
    wu_by_date = db["WU_by_date"]
    total_wins_count = len(wu_by_date.keys())
    win_data = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db["WU_scores"])))
    try:
        user_win_count = win_data[str(user_id)][1]
    except KeyError:
        user_win_count = 0
    return user_win_count / total_wins_count


def user_win_rate_graph_lm(user_id):
    lm_by_date = db["LM_by_date"]
    total_count = 0
    win_count = 0
    y = []
    x = []
    for date in lm_by_date:
        if lm_by_date[date] == user_id:
            win_count += 1
        total_count += 1
        y.append((win_count / total_count) * 100)
        x.append(datetime.strptime(date, "%Y-%m-%d"))
    plt.clf()
    plt.plot_date(x, y, "-")
    plt.gcf().autofmt_xdate()
    plt.xlabel("Date")
    plt.ylabel("Win Rate (%)")
    plt.title("Last Message Of The Day Performance")
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)
    return Image.open(image_stream)


def user_win_rate_graph_wu(user_id):
    wu_by_date = db["WU_by_date"]
    total_count = 0
    win_count = 0
    y = []
    x = []
    for date in wu_by_date:
        if wu_by_date[date] == user_id:
            win_count += 1
        total_count += 1
        y.append((win_count / total_count) * 100)
        x.append(datetime.strptime(date, "%Y-%m-%d"))
    plt.clf()
    plt.plot_date(x, y, "-")
    plt.gcf().autofmt_xdate()
    plt.xlabel("Date")
    plt.ylabel("Win Rate (%)")
    plt.title("Waking Up Early Award Performance")
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)
    return Image.open(image_stream)


def user_performance_graphs(user_id):
    image1 = user_win_rate_graph_wu(user_id)
    image2 = user_win_rate_graph_lm(user_id)
    height = max(image1.size[1], image2.size[1])
    image1 = image1.resize((int(image1.size[0] * height / image1.size[1]), height))
    image2 = image2.resize((int(image2.size[0] * height / image2.size[1]), height))
    new_width = image1.size[0] + image2.size[0]
    joined_image = Image.new('RGB', (new_width, height))
    joined_image.paste(image1, (0, 0))
    joined_image.paste(image2, (image1.size[0], 0))
    joined_image.save("graphs.png")
    return discord.File("graphs.png", filename="graphs.png")


def all_users_win_rate_graph(db_key):  # win rate against time
    return


def has_dates(dictionary):
    for key in dictionary:
        if len(dictionary[key]) != 0:
            return True
    return False


def string_to_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def generate_winner_by_date_datastructure():
    with open("wu_wins.json", 'r') as file:
        wu_json = json.load(file)

    with open("lm_wins.json", 'r') as file:
        lm_json = json.load(file)

    WU_by_date = {}
    LM_by_date = {}

    while has_dates(wu_json):
        smallest_date = "2100-01-01"
        smallest_date_key = ""
        for key in wu_json:
            if len(wu_json[key]) > 0 and string_to_date(wu_json[key][0]) < string_to_date(smallest_date):
                smallest_date = wu_json[key][0]
                smallest_date_key = key

        wu_json[smallest_date_key].pop(0)
        WU_by_date[smallest_date] = smallest_date_key

    while has_dates(lm_json):
        smallest_date = "2100-01-01"
        smallest_date_key = ""
        for key in lm_json:
            if len(lm_json[key]) > 0 and string_to_date(lm_json[key][0]) < string_to_date(smallest_date):
                smallest_date = lm_json[key][0]
                smallest_date_key = key

        lm_json[smallest_date_key].pop(0)
        LM_by_date[smallest_date] = smallest_date_key

    WU_by_date_json = json.dumps(WU_by_date)
    LM_by_date_json = json.dumps(LM_by_date)

    with open("WU_by_date.json", "w") as file:
        file.write(WU_by_date_json)
    with open("LM_by_date.json", "w") as file:
        file.write(LM_by_date_json)
