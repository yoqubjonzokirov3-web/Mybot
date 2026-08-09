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

user_data = {}

def get_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {"lang": None, "history": []}
    return user_data[chat_id]

def tizim_prompt(lang):
    if lang == "uz":
        return "Sen har doim faqat o'zbek tilida javob berasan."
    elif lang == "ru":
        return "Ты всегда отвечаешь только на русском языке."
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
        "model": "openai/gpt-oss-120b",
        "messages": messages
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )
    result = response.json()
    javob = result["choices"][0]["message"]["content"]
    
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
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    bot.send_message(message.chat.id, "Tilni tanlang / Choose a language / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def til_tanlandi(call):
    lang = call.data.replace("lang_", "")
    user = get_user(call.message.chat.id)
    user["lang"] = lang
    user["history"] = []
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    xabarlar = {
        "uz": "Salom! Menga savol yozing yoki ovozli xabar yuboring 🤖",
        "en": "Hello! Send me a question in text or voice 🤖",
        "ru": "Привет! Напишите вопрос или отправьте голосовое сообщение 🤖"
    }
    bot.send_message(call.message.chat.id, xabarlar[lang])

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
            xatolar = {
                "uz": "Ovozni tushuna olmadim, qayta urinib ko'ring.",
                "en": "Couldn't understand the voice, try again.",
                "ru": "Не удалось распознать голос, попробуйте снова."
            }
            bot.reply_to(message, xatolar.get(user["lang"], "Xatolik"))
            return
        
        javob = ai_javob(chat_id, matn)
        bot.reply_to(message, javob)
        
    except Exception as e:
        xatolar = {
            "uz": "Xatolik yuz berdi 😔",
            "en": "An error occurred 😔",
            "ru": "Произошла ошибка 😔"
        }
        bot.reply_to(message, xatolar.get(user["lang"], "Xatolik 😔"))
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
        xatolar = {
            "uz": "Kechirasiz, xatolik yuz berdi 😔",
            "en": "Sorry, an error occurred 😔",
            "ru": "Извините, произошла ошибка 😔"
        }
        bot.reply_to(message, xatolar.get(user["lang"], "Xatolik 😔"))
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
