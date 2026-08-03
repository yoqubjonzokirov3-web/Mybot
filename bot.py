import os
import telebot
import time
import requests
import threading
from flask import Flask

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def ai_javob(savol):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Sen har doim faqat o'zbek tilida javob berasan. Boshqa tilda hech qachon javob yozma, hatto savol boshqa tilda berilsa ham, javobni o'zbek tiliga tarjima qilib ber."},
            {"role": "user", "content": savol}
        ]
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Menga har qanday savol bering, javob beraman 🤖")

@bot.message_handler(func=lambda message: True)
def javob_ber(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        javob = ai_javob(message.text)
        bot.reply_to(message, javob)
    except Exception as e:
        bot.reply_to(message, "Kechirasiz, xatolik yuz berdi 😔")
        print(f"AI xatolik: {e}")

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Xatolik: {e}")
            time.sleep(5)

@app.route('/')
def home():
    return "Bot ishlayapti!"

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=10000)
