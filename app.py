from flask import Flask, render_template, request, redirect, url_for
from collections import deque
import sqlite3
from datetime import datetime

app = Flask(__name__)

TOTAL_PLATFORMS = 3
MAX_QUEUE = 5

platforms = [None] * TOTAL_PLATFORMS
waiting_queue = deque()


def init_db():
    conn = sqlite3.connect("railway.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS train_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_no TEXT,
        arrival_time TEXT,
        departure_time TEXT,
        platform INTEGER,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


def log_event(train_no, arrival, departure, platform, status):

    conn = sqlite3.connect("railway.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO train_logs
    (train_no, arrival_time, departure_time, platform, status)
    VALUES (?, ?, ?, ?, ?)
    """, (train_no, arrival, departure, platform, status))

    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template(
        "railway.html",
        platforms=platforms,
        queue=list(waiting_queue)
    )


@app.route("/arrival", methods=["POST"])
def arrival():

    train_no = request.form.get("train_no")

    if not train_no:
        return redirect(url_for("index"))

    if not train_no.isdigit() or len(train_no) != 5:
        return "Train number must be exactly 5 digits"

    if train_no in platforms or train_no in waiting_queue:
        return "Train already exists in station"

    arrival_time = datetime.now().strftime("%H:%M:%S")

    for i in range(TOTAL_PLATFORMS):

        if platforms[i] is None:

            platforms[i] = train_no

            log_event(train_no, arrival_time, None, i + 1, "Arrived")

            return redirect(url_for("index"))

    if len(waiting_queue) >= MAX_QUEUE:
        return "Queue Full. Train cannot enter station."

    waiting_queue.append(train_no)

    log_event(train_no, arrival_time, None, None, "Waiting")

    return redirect(url_for("index"))


@app.route("/departure", methods=["POST"])
def departure():

    train_no = request.form.get("train_no")

    if not train_no:
        return redirect(url_for("index"))

    departure_time = datetime.now().strftime("%H:%M:%S")

    found = False

    for i in range(TOTAL_PLATFORMS):

        if platforms[i] == train_no:

            found = True

            platforms[i] = None

            log_event(train_no, None, departure_time, i + 1, "Departed")

            if waiting_queue:

                next_train = waiting_queue.popleft()

                platforms[i] = next_train

                log_event(
                    next_train,
                    datetime.now().strftime("%H:%M:%S"),
                    None,
                    i + 1,
                    "Assigned from Queue"
                )

            break

    if not found:
        return "Train not found on any platform"

    return redirect(url_for("index"))


@app.route("/logs")
def logs():

    conn = sqlite3.connect("railway.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM train_logs ORDER BY id DESC")

    data = cursor.fetchall()

    conn.close()

    return render_template("logs.html", logs=data)


@app.route("/search", methods=["GET", "POST"])
def search():

    result = None

    if request.method == "POST":

        train_no = request.form.get("train_no")

        if not train_no.isdigit() or len(train_no) != 5:
            result = "Train number must be 5 digits"

        elif train_no in platforms:
            result = f"Train {train_no} is at Platform {platforms.index(train_no) + 1}"

        elif train_no in waiting_queue:
            result = "Train is waiting in queue"

        else:
            result = "Train not found"

    return render_template("search.html", result=result)

@app.route("/overview")
def overview():

    conn = sqlite3.connect("railway.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM train_logs")
    total_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM train_logs WHERE status='Arrived'")
    arrivals = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM train_logs WHERE status='Departed'")
    departures = cursor.fetchone()[0]

    conn.close()

    occupied = sum(1 for p in platforms if p is not None)
    available = TOTAL_PLATFORMS - occupied

    return render_template(
        "overview.html",
        total_platforms=TOTAL_PLATFORMS,
        occupied=occupied,
        available=available,
        queue_size=len(waiting_queue),
        total_logs=total_logs,
        arrivals=arrivals,
        departures=departures
    )


if __name__ == "__main__":
    app.run(debug=True)