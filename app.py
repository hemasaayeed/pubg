import os
import re
import sqlite3
import time
from flask import Flask, request, jsonify, send_from_directory

# ============ الإعدادات ============
# حط التوكن اللي هتاخده من BotFather هنا، أو كـ environment variable اسمه BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
# سر بسيط بيتحط في رابط الـ webhook عشان محدش تاني يقدر يبعتلك بيانات وهمية
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "change-this-secret")

DB_PATH = os.path.join(os.path.dirname(__file__), "posts.db")

app = Flask(__name__, static_folder="static", static_url_path="")


# بتحاول تلاقي السعر جوه نص البوست، بتفهم صيغ زي:
# "السعر 1500" / "بسعر: 2000 جنيه" / "10 الف" / "15,000"
def extract_price(text):
    if not text:
        return None

    # صيغة "رقم + الف" مثل "10 الف" أو "15الف" = 10000, 15000
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:الف|ألف|k)\b", text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 1000)

    # صيغة عادية بجانب كلمة السعر/بسعر، لتقليل الالتباس مع أرقام تانية في النص
    m = re.search(r"(?:السعر|بسعر|سعر)\D{0,10}(\d[\d,\.]{1,9})", text)
    if m:
        return int(m.group(1).replace(",", "").split(".")[0])

    # آخر حل: أول رقم كبير (3 أرقام فأكثر) في النص
    m = re.search(r"\b(\d{3,7})\b", text.replace(",", ""))
    if m:
        return int(m.group(1))

    return None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            message_id INTEGER PRIMARY KEY,
            text TEXT,
            media_type TEXT,
            media_file_id TEXT,
            price INTEGER,
            date INTEGER,
            received_at INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# تليجرام هيبعت كل بوست جديد في القناة على الرابط ده أول ما ينزل
@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def telegram_webhook():
    update = request.get_json(force=True, silent=True) or {}

    # بوستات القنوات بتيجي جوه channel_post
    post = update.get("channel_post") or update.get("edited_channel_post")
    if not post:
        return jsonify({"ok": True})  # نوع تحديث مش مهتمين بيه، نتجاهله

    message_id = post.get("message_id")
    text = post.get("text") or post.get("caption") or ""
    date = post.get("date", int(time.time()))

    media_type = None
    media_file_id = None
    for key in ("photo", "video", "document", "animation"):
        if key in post:
            media_type = key
            media_file_id = (
                post[key][-1]["file_id"] if key == "photo" else post[key]["file_id"]
            )
            break

    price = extract_price(text)

    conn = get_db()
    conn.execute(
        """
        INSERT INTO posts (message_id, text, media_type, media_file_id, price, date, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET text=excluded.text, price=excluded.price
        """,
        (message_id, text, media_type, media_file_id, price, date, int(time.time())),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# فئات السعر المتاحة للفلترة
PRICE_TIERS = {
    "under_2000": (0, 2000),
    "under_10000": (0, 10000),
    "under_20000": (0, 20000),
}


def row_to_post(r):
    media_url = f"/api/media/{r['media_file_id']}" if r["media_file_id"] else None
    return {
        "id": r["message_id"],
        "text": r["text"],
        "date": r["date"],
        "media_type": r["media_type"],
        "media_url": media_url,
        "price": r["price"],
    }


# الفرونت إند بيسحب آخر البوستات من هنا كل شوية، مع دعم فلتر السعر
# مثال: /api/posts?tier=under_10000
@app.route("/api/posts")
def api_posts():
    tier = request.args.get("tier")
    conn = get_db()

    if tier and tier in PRICE_TIERS:
        _, max_price = PRICE_TIERS[tier]
        rows = conn.execute(
            "SELECT * FROM posts WHERE price IS NOT NULL AND price <= ? ORDER BY date DESC LIMIT 100",
            (max_price,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY date DESC LIMIT 100"
        ).fetchall()

    conn.close()
    return jsonify([row_to_post(r) for r in rows])


# حسابات معروضة من شهر تقريبًا فأكتر (يعني قديمة ولسه موجودة) - بتترشح للزائر
@app.route("/api/suggested")
def api_suggested():
    thirty_days_ago = int(time.time()) - 30 * 24 * 60 * 60
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM posts WHERE date <= ? ORDER BY date DESC LIMIT 20",
        (thirty_days_ago,),
    ).fetchall()
    conn.close()
    return jsonify([row_to_post(r) for r in rows])


# بروكسي بسيط عشان نجيب الصور/الفيديوهات من تليجرام باستخدام الـ file_id
@app.route("/api/media/<file_id>")
def api_media(file_id):
    import requests

    file_info = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
        params={"file_id": file_id},
    ).json()
    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    resp = requests.get(file_url)
    return resp.content, 200, {"Content-Type": resp.headers.get("Content-Type", "application/octet-stream")}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
