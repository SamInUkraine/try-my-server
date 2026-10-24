import os
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config["SECRET_KEY"] = "demo-privacy"
socketio = SocketIO(app, cors_allowed_origins="*")

# Прості кольори, щоб відрізняти пальці різних людей на панелі.
COLORS = [("red", "червоний"), ("blue", "синій"), ("green", "зелений"),
          ("orange", "помаранчевий"), ("purple", "фіолетовий"),
          ("brown", "коричневий"), ("magenta", "малиновий"),
          ("teal", "бірюзовий")]

MAX_TEXT = 300
MAX_HISTORY = 600

visitors = {}            # sid -> дані про відвідувача
counter = {"n": 0}


def public(sid, v):
    return {"id": sid, "num": v["num"],
            "color": v["color"], "colorname": v["colorname"],
            "device": v["device"], "text": v["text"],
            "submitted": v["submitted"]}


@app.route("/")
def index():
    return render_template("phone.html")


@app.route("/panel")
def panel():
    return render_template("panel.html")


# --- Телефон глядача ------------------------------------------------------

@socketio.on("hello_phone")
def hello_phone(data):
    """Телефон приєднується ПІСЛЯ згоди. data містить інфо про пристрій."""
    if request.sid in visitors:
        return
    counter["n"] += 1
    n = counter["n"]
    color, colorname = COLORS[(n - 1) % len(COLORS)]
    visitors[request.sid] = {
        "num": n, "color": color, "colorname": colorname,
        "device": data.get("device", {}),
        "text": "", "history": [], "submitted": None,
    }
    emit("visitor_join", public(request.sid, visitors[request.sid]), to="panel")
    emit("you_are", {"num": n})


@socketio.on("typing")
def on_typing(data):
    v = visitors.get(request.sid)
    if not v:
        return
    text = str(data.get("text", ""))[:MAX_TEXT]
    v["text"] = text
    v["history"].append({"t": time.time(), "text": text})
    if len(v["history"]) > MAX_HISTORY:
        v["history"].pop(0)
    emit("typing", {"id": request.sid, "text": text}, to="panel")


@socketio.on("touch")
def on_touch(data):
    v = visitors.get(request.sid)
    if not v:
        return
    emit("touch", {"id": request.sid, "color": v["color"],
                   "x": data.get("x", 0), "y": data.get("y", 0),
                   "down": data.get("down", False)}, to="panel")


# --- Панель для проектора -------------------------------------------------

@socketio.on("hello_panel")
def hello_panel():
    join_room("panel")
    emit("state", [public(s, v) for s, v in visitors.items()])


@socketio.on("disconnect")
def on_disconnect():
    if visitors.pop(request.sid, None):
        emit("visitor_leave", {"id": request.sid}, to="panel")


if __name__ == "__main__":
    # В облаці хостинг сам задає порт через змінну PORT.
    # Локально, якщо її немає, беремо 5000.
    port = int(os.environ.get("PORT", 5000))
    print("Панель для проектора:  http://localhost:%d/panel" % port)
    print("Сторінка для телефонів: http://<твій-IP>:%d/" % port)
    socketio.run(app, host="0.0.0.0", port=port, debug=False,
                 allow_unsafe_werkzeug=True)
