from flask import Flask
from config import PORT

app = Flask(__name__)

@app.route("/")
def home():
    return "TamilMV + TamilBlasters Bot Running"


def run_web():
    app.run(host="0.0.0.0", port=PORT)
