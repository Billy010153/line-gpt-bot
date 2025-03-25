import os
import threading
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

# 讀取個人資料
def load_user_profile():
    try:
        with open("user_profile.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return "\n".join(lines)
    except:
        return ""

USER_PROFILE = load_user_profile()

def process_event(event):
    try:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event.get("replyToken")
            if not reply_token:
                print("❌ 無效的 replyToken")
                return

            # 使用個人資料作為系統 prompt
            system_prompt = f"""你是一位叫「自樂」的台灣人。請根據以下真實生活背景，代替本人用第一人稱簡單且輕鬆愉快地回答別人的問題。

{USER_PROFILE}

請用自然語氣回應以下問題："""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
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
        print("❌ 錯誤：", str(e))

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()
    print("📩 收到 LINE Webhook:", body)
    if "events" in body:
        for event in body["events"]:
            threading.Thread(target=process_event, args=(event,)).start()
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return "我是本人 LINE Bot 已上線！"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
