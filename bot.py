import os
import telebot
import time
import requests
import threading
from flask import Flask
from telebot import types

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Har bir foydalanuvchi uchun til va suhbat tarixini saqlaymiz
user_data = {}

def get_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {"lang": None, "history": []}
    return user_data[chat_id]

def tizim_prompt(lang):
    if lang == "uz":
        return "Sen har doim faqat o'zbek tilida javob berasan."
    else:
        return "You always respond only in English."

def ai_javob(chat_id, savol):
    user = get_user(chat_id)
    lang = user["lang"] or "uz"
    
    messages = [{"role": "system", "content": tizim_prompt(lang)}]
    messages += user["history"]
    messages.append({"role": "user", "content": savol})
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )
    result = response.json()
    javob = result["choices"][0]["message"]["content"]
    
    # Tarixga qo'shamiz, faqat oxirgi 10 ta xabarni saqlaymiz
    user["history"].append({"role": "user", "content": savol})
    user["history"].append({"role": "assistant", "content": javob})
    user["history"] = user["history"][-10:]
    
    return javob

def ovozni_matnga(file_path):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"model": "whisper-large-v3"}
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers=headers,
            files=files,
            data=data
        )
    result = response.json()
    return result.get("text", "")

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "Tilni tanlang / Choose a language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def til_tanlandi(call):
    lang = "uz" if call.data == "lang_uz" else "en"
    user = get_user(call.message.chat.id)
    user["lang"] = lang
    user["history"] = []
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    if lang == "uz":
        bot.send_message(call.message.chat.id, "Salom! Menga savol yozing yoki ovozli xabar yuboring 🤖")
    else:
        bot.send_message(call.message.chat.id, "Hello! Send me a question in text or voice 🤖")

@bot.message_handler(content_types=['voice'])
def ovozli_xabar(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    if not user["lang"]:
        bot.reply_to(message, "Iltimos, avval /start bosing / Please press /start first")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open("voice.ogg", "wb") as f:
            f.write(downloaded_file)
        
        matn = ovozni_matnga("voice.ogg")
        os.remove("voice.ogg")
        
        if not matn:
            bot.reply_to(message, "Ovozni tushuna olmadim, qayta urinib ko'ring." if user["lang"] == "uz" else "Couldn't understand the voice, try again.")
            return
        
        javob = ai_javob(chat_id, matn)
        bot.reply_to(message, javob)
        
    except Exception as e:
        bot.reply_to(message, "Xatolik yuz berdi 😔" if user["lang"] == "uz" else "An error occurred 😔")
        print(f"Ovoz xatolik: {e}")

@bot.message_handler(func=lambda message: True)
def javob_ber(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    if not user["lang"]:
        bot.reply_to(message, "Iltimos, avval /start bosing / Please press /start first")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    try:
        javob = ai_javob(chat_id, message.text)
        bot.reply_to(message, javob)
    except Exception as e:
        bot.reply_to(message, "Kechirasiz, xatolik yuz berdi 😔" if user["lang"] == "uz" else "Sorry, an error occurred 😔")
        print(f"AI xatolik: {e}")

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Polling xatolik: {e}")

@app.route('/')
def home():
    return "Bot ishlayapti!"

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=10000)
