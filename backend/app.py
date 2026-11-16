import os
from flask import Flask, jsonify

app = Flask(__name__)
SERVER_NAME = os.environ.get("SERVER_NAME", "unknown")


@app.route("/")
def index():
    return jsonify(server=SERVER_NAME, status="ok")


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
