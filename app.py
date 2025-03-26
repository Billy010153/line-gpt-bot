import os
import threading
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

conversation_histories = {}
MAX_HISTORY = 5
PREFERRED_MODEL = "gpt-4-turbo"
FALLBACK_MODEL = "gpt-3.5-turbo"

def load_user_profile():
    try:
        with open("user_profile.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return "\n".join(lines)
    except Exception as e:
        print("載入個人資料失敗：", str(e))
        return ""

USER_PROFILE = load_user_profile()

def process_event(event):
    try:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event.get("replyToken")
            user_id = event.get("source", {}).get("userId", "anonymous")

            if not reply_token:
                print("❌ 無效的 replyToken")
                return

            system_prompt = f"""你是一位叫「自樂」的台灣人，請把用戶當作好朋友，以簡單明瞭且輕鬆幽默的語氣回答，以下是你的真實背景資料：

{USER_PROFILE}
"""

            if user_id not in conversation_histories:
                conversation_histories[user_id] = [
                    {"role": "system", "content": system_prompt}
                ]

            history = conversation_histories[user_id]
            history.append({"role": "user", "content": user_message})

            try:
                response = client.chat.completions.create(
                    model=PREFERRED_MODEL,
                    messages=history
                )
            except Exception as e:
                print("⚠️ GPT-4-Turbo 發生錯誤，降級至 GPT-3.5：", e)
                response = client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=history
                )

            reply_message = response.choices[0].message.content.strip()
            history.append({"role": "assistant", "content": reply_message})
            if len(history) > MAX_HISTORY + 1:
                conversation_histories[user_id] = history[-(MAX_HISTORY + 1):]

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
    return "我是本人 LINE Bot（支援自動降級模型）已啟動！"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
