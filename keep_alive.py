from flask import Flask, render_template, send_from_directory
from threading import Thread
from replit import db


def convert_observed_dict_to_dict(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, 'value'):
        return convert_observed_dict_to_dict(data.value)
    else:
        return data


app = Flask(' ')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/wakingup')
def wakingup():
    return dict(db["WUscores"])


@app.route('/lastmessage')
def lastmessage():
    return dict(db["LMscores"])


@app.route('/streaks')
def streaks():
    return convert_observed_dict_to_dict(db["streak"])


def run():
    app.run(host="0.0.0.0", port=8081)


def keep_alive():
    t = Thread(target=run)
    t.start()
