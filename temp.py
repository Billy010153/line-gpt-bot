import os
import threading
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

# 從環境變數讀取 API Key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

LINE_ACCESS_TOKEN = os.environ.get("z5Yth8CICDGUJVV4HRmLbhorsQrxyvqDEJpr/bSORt+PXuN/mOK4uzhvJ8KveV0mKgg8SpzjJcLAlsKt6NGmVWtV6P1oSflP6QQNL4YpiQWAXUjVyG5DH5PNJsslKpehSfWZS+PWxvrERybqyzoXsQdB04t89/1O/w1cDnyilFU=")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

def process_event(event):
    try:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event.get("replyToken")

            if not reply_token:
                print("❌ 無效的 replyToken")
                return

            print("✅ GPT 收到問題：", user_message)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位親切的 AI 助手"},
                    {"role": "user", "content": user_message}
                ]
            )

            reply_message = response.choices[0].message.content.strip()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
            }

            payload = {
                "replyToken": reply_token,
                "messages": [{"type": "text", "text": reply_message}]
            }

            r = requests.post(LINE_REPLY_URL, headers=headers, json=payload)
            print("📤 傳送至 LINE 狀態：", r.status_code)

    except Exception as e:
        print("❌ 處理過程發生錯誤：", str(e))

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()
    print("📩 收到 LINE Webhook:", body)

    if "events" in body:
        for event in body["events"]:
            threading.Thread(target=process_event, args=(event,)).start()

    return jsonify({"status": "ok"})  # ✅ 立刻回應 LINE
