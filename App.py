import os, requests, random
from flask import Flask, request, Response
app = Flask(__name__)
TOKEN = "8121251248:AAGw5qQh5MbjN_JwPvpPWPWBoO0zE2dMGLw"
API_URL = f"https://api.telegram.org/bot{TOKEN}"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
ULTRA_STYLE = """Ultra-realistic photo of {PROMPT}, 8k, sharp focus, detailed skin texture"""
def call_gemini(prompt):
    if not GOOGLE_API_KEY: return prompt
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    data = {"contents": [{"parts": [{"text": ULTRA_STYLE.replace("{PROMPT}", prompt)}]}]}
    try:
        r = requests.post(url, json=data, timeout=30)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: return prompt
def gen_image(p):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(p)}?width=1024&height=1280&nologo=true&seed={random.randint(1,999999)}"
    try:
        r = requests.get(url, timeout=40)
        if r.status_code==200: return r.content
    except: pass
    return None
@app.route('/', methods=['GET'])
def home(): return "SAGESSE ONLINE",200
@app.route('/', methods=['POST'])
def webhook():
    data=request.get_json()
    if not data or "message" not in data: return Response("ok",200)
    msg=data["message"]; chat_id=msg["chat"]["id"]
    if "text" in msg:
        t=msg["text"]
        if t=="/start": send_message(chat_id,"Salut chef! Envoie ton prompt ULTRA")
        else:
            send_message(chat_id,f"SAGESSE travaille: {t}")
            img=gen_image(call_gemini(t))
            if img: send_photo(chat_id,img,f"SAGESSE: {t}")
            else: send_message(chat_id,"Erreur reessaie")
    return Response("ok",200)
def send_message(c,t): requests.post(f"{API_URL}/sendMessage",json={"chat_id":c,"text":t})
def send_photo(c,d,cap=""):
    requests.post(f"{API_URL}/sendPhoto",files={'photo':('s.jpg',d)},data={'chat_id':c,'caption':cap})
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
