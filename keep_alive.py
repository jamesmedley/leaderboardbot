from flask import Flask, render_template, send_from_directory
from threading import Thread
from replit import db
import discord_user_data


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


def sort_leaderboard(db_key):
    last_message_scores = convert_observed_list_to_list(convert_observed_dict_to_dict(dict(db[db_key])))
    sorted_scores = sorted(last_message_scores.items(), key=lambda x: x[1][1], reverse=True)
    users_info = []
    for user_id, score in sorted_scores:
        user_info = discord_user_data.get_user_info(user_id)
        if user_info:
            users_info.append((user_info["username"], user_info["profile_picture"], score[1]))
    return users_info


app = Flask(" ")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)


@app.route("/wakingup")
def wakingup():
    users_info = sort_leaderboard("WU_scores")
    return render_template("leaderboard.html", leaderboard=users_info, title="Waking Up Early Award",
                           tab_title="Waking Up Leaderboard")


@app.route("/lastmessage")
def lastmessage():
    users_info = sort_leaderboard("LM_scores")
    return render_template("leaderboard.html", leaderboard=users_info, title="Last Message Of The Day Award",
                           tab_title="Last Message Leaderboard")


@app.route("/streaks")
def streaks():
    streaks_data = convert_observed_dict_to_dict(db["streak"])
    lm_streak_holder_id = list(streaks_data["LM"].keys())[0]
    wu_streak_holder_id = list(streaks_data["WU"].keys())[0]
    lm_user_info = discord_user_data.get_user_info(lm_streak_holder_id)
    wu_user_info = discord_user_data.get_user_info(wu_streak_holder_id)
    lm_streak = streaks_data["LM"][lm_streak_holder_id]
    wu_streak = streaks_data["WU"][wu_streak_holder_id]
    lm_data = {"username": lm_user_info["username"], "profile_picture": lm_user_info["profile_picture"],
               "streak": lm_streak, "award": "Last Message Of The Day"}
    wu_data = {"username": wu_user_info["username"], "profile_picture": wu_user_info["profile_picture"],
               "streak": wu_streak, "award": "Waking Up Early Award"}
    return render_template('streaks.html', lm=lm_data, wu=wu_data, title="Streaks")


@app.route("/docs")
def docs():
    return render_template('docs.html')


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
