from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    app.run(host='0.0.0.0', port=8080)

# function to be used in main.py
def bud_alive():
    t = Thread(target=run)
    t.start()
