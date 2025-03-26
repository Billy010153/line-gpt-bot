import os
import threading
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

# 初始化 OpenAI client，從環境變數讀取金鑰
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

# 全域記憶字典：以使用者 ID 為 key，儲存對話歷史（列表）
conversation_histories = {}
MAX_HISTORY = 5  # 可調整保留最近幾則對話

def load_user_profile():
    """
    載入個人資料，作為系統提示的一部份。
    """
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
            if not reply_token:
                print("❌ 無效的 replyToken")
                return

            # 取得使用者 ID，若無則用 "anonymous"
            user_id = event.get("source", {}).get("userId", "anonymous")
            print(f"✅ 收到 {user_id} 的訊息：{user_message}")

            # 準備系統提示：將你的個人資料與角色說明傳給 GPT
            system_prompt = f"""你是一位叫「自樂」的台灣人，請把用戶當作好朋友，以簡單明瞭且輕鬆幽默的語氣回答，以下是你的真實背景資料：
{USER_PROFILE}

請根據以上資訊，用第一人稱且親切自然地回答問題。"""

            # 取得該使用者的對話歷史，若無則初始化
            if user_id not in conversation_histories:
                conversation_histories[user_id] = [
                    {"role": "system", "content": system_prompt}
                ]
            history = conversation_histories[user_id]

            # 將最新的使用者訊息加入對話歷史
            history.append({"role": "user", "content": user_message})

            # 呼叫 OpenAI API 取得回應
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=history
            )
            reply_message = response.choices[0].message.content.strip()

            # 將 AI 回覆也加入對話歷史
            history.append({"role": "assistant", "content": reply_message})
            # 保留最新 MAX_HISTORY 條對話（包含 system prompt）
            if len(history) > MAX_HISTORY + 1:  # +1 因為第一筆是 system prompt
                conversation_histories[user_id] = history[-(MAX_HISTORY + 1):]

            print(f"💬 回覆給 {user_id}：{reply_message}")

            # 發送回覆給 LINE
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
