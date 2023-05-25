from flask import Flask
from threading import Thread
import json

app = Flask(' ')

@app.route('/')
def home():
    return """
    <h1>Leaderboard bot</h1>
    <ul>
        <li><a href="/wakingup">Waking Up Award</a></li>
        <li><a href="/lastmessage">Last Message Of The Day</a></li>
        <li><a href="/streaks">Streaks</a></li>
    </ul>
    """

@app.route('/wakingup')
def wakingup():
  with open("WUscores.json", "r") as f:
    data = json.load(f)
  f.close()
  return data

@app.route('/lastmessage')
def lastmessage():
  with open("LMscores.json", "r") as f:
    data = json.load(f)
  f.close()
  return data

@app.route('/streaks')
def streaks():
  with open("streak.json", "r") as f:
    data = json.load(f)
  f.close()
  return data

def run():
  app.run(host = "0.0.0.0", port = 8081)

def keep_alive():
  t= Thread(target=run)
  t.start()