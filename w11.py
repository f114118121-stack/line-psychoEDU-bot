# -*- coding: utf-8 -*-
"""
改寫版本 - LINE Bot + Gemini API + FastAPI
可部署 Render，接收 LINE 訊息並回覆心理教育小百科
"""

from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
from dotenv import load_dotenv
import os

# ======== 載入 .env ========
load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ======== LINE SDK 初始化 ========
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ======== Gemini (Google AI Studio) 初始化 ========
ai_model = "gemini-2.5-flash-lite"

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    timeout=60.0
)

# ======== 系統提示詞：心理教育小百科 ========
psychoedu_prompt = """
你是一個「心理教育與情緒小百科」聊天機器人，主要對象是有社群媒體使用經驗的青少年與青年。
你的工作是用簡單、溫和的繁體中文，解釋心理健康與情緒相關的知識。

【可以做的事】
1. 解釋基本情緒概念，例如開心、生氣、害怕、悲傷、焦慮、壓力等。
2. 說明「憂鬱情緒」與一般情緒波動的不同。
3. 說明壓力、人際關係、社群媒體、上行比較、自尊與情緒的關聯。
4. 提供一般性的自我照顧建議，如睡眠、運動、放鬆、寫日記等。
5. 說明何時建議尋求專業協助。

【不能做的事】
1. 不做診斷，不說使用者有病或沒病。
2. 不提供治療計畫或醫療建議。
3. 不鼓勵拒醫。
4. 若超出心理教育範圍，要提醒尋求專業協助。

【危險訊息時】
1. 表達關心。
2. 說明自己不是緊急協助者。
3. 鼓勵找可信任的人或緊急專業資源。
4. 提醒安全很重要。

【語氣】
- 溫和、好懂、生活化的繁體中文。
- 短句，3~5 段為主。
- 可用簡單比喻。
"""

# ======== FastAPI 啟動 ========
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "LINE Bot with Gemini is running"}

# ======== LINE webhook API ========
@app.post("/webhook")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

# ======== 訊息事件處理 ========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()

    try:
        # 呼叫 Google Gemini
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": psychoedu_prompt},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=250,
            temperature=0.7
        )

        ai_reply = response.choices[0].message.content.strip()

    except Exception as e:
        ai_reply = f"抱歉，我這邊遇到一些問題：{str(e)}"

    # 回覆 LINE 使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )
