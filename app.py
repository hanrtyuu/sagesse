from flask import Flask, request, jsonify, render_template_string, send_file, session, redirect, url_for
import io, os, requests, json
from PIL import Image, ImageFilter

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sagesse-secret-2026")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or "AQ.Ab8RN6JK6k5fhjKCAqnjm2jNwee9IIIumTBN9fAnkcYAUfE_8Q"
MEM_FILE = "memoire.json"
USER_FILE = "users.json"

def load_memoire():
    try:
        if os.path.exists(MEM_FILE):
            with open(MEM_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: pass
    return []

def save_memoire(q, r):
    try:
        m=load_memoire(); m.append({"q":q,"r":r}); m=m[-100:]
        with open(MEM_FILE,'w',encoding='utf-8') as f: json.dump(m,f,ensure_ascii=False,indent=2)
    except: pass

def load_users():
    try:
        if os.path.exists(USER_FILE):
            with open(USER_FILE,'r',encoding='utf-8') as f: return json.load(f)
    except: pass
    return {}

def save_user(email, data):
    try:
        u=load_users(); u[email]=data
        with open(USER_FILE,'w',encoding='utf-8') as f: json.dump(u,f,ensure_ascii=False,indent=2)
    except: pass

SYSTEM_GPT = """
Tu es SAGESSE, une IA super intelligente comme ChatGPT-4o / Claude 3.5.
Règles d'intelligence:
1. Réfléchis étape par étape avant de répondre.
2. Sois utile, précis, profond. Donne des exemples concrets si besoin.
3. Si c'est du code: explique + donne le code propre.
4. Si c'est une question complexe: structure ta réponse avec titres, listes.
5. Adapte-toi à la langue de l'utilisateur. Tu parles français sauf si on te parle autre langue.
6. Tu as une mémoire de 100 messages, utilise-la.
7. Tu es sage, pas bavard inutile. Direct et intelligent.
8. Ne dis jamais que tu es Gemini ou Pollinations. Tu es SAGESSE.
"""

# PAGE LOGIN AVEC GOOGLE + EMAIL
LOGIN_HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SAGESSE - Connexion</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#f5f5f5;height:100dvh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;padding:30px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.1);width:90%;max-width:380px;text-align:center}
.logo{font-size:32px;font-weight:800;margin-bottom:8px}
.sub{color:#666;margin-bottom:25px;font-size:14px}
.btn{width:100%;padding:14px;border-radius:30px;border:1px solid #ddd;background:#fff;display:flex;align-items:center;justify-content:center;gap:10px;font-weight:600;margin-bottom:12px;cursor:pointer;font-size:15px}
.btn-google{border-color:#ddd}
.btn-email{background:#000;color:#fff;border-color:#000}
input{width:100%;padding:14px;border-radius:30px;border:1px solid #ddd;outline:none;font-size:15px;margin-bottom:12px}
.divider{margin:18px 0;color:#999;font-size:13px;display:flex;align-items:center;gap:10px}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:#eee}
</style></head><body>
<div class="card">
<div class="logo">SAGESSE</div>
<div class="sub">Connecte-toi pour continuer</div>

<button class="btn btn-google" onclick="googleLogin()"> <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="20"> Continuer avec Google</button>

<div class="divider">ou</div>

<input id="email" type="email" placeholder="Ton email">
<input id="nom" type="text" placeholder="Ton prénom">
<button class="btn btn-email" onclick="emailLogin()">Continuer avec Email →</button>

<p style="font-size:11px;color:#999;margin-top:15px">En continuant, tu acceptes les conditions de SAGESSE</p>
</div>
<script>
function googleLogin(){
 // Pour l'instant on redirige vers login Google (on va configurer après)
 window.location.href='/auth/google';
}
function emailLogin(){
 let email=document.getElementById('email').value.trim();
 let nom=document.getElementById('nom').value.trim();
 if(!email ||!nom){ alert('Remplis email et prénom'); return; }
 fetch('/auth/email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,nom})})
.then(r=>r.json()).then(d=>{
   if(d.ok) window.location.href='/';
   else alert(d.error);
 });
}
</script></body></html>
"""

HTML = """
<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>SAGESSE</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{display:flex;flex-direction:column;background:#f5f5f5;height:100dvh}
.top{height:50px;display:flex;align-items:center;padding:0 15px;border-bottom:1px solid #ddd;font-weight:700;justify-content:space-between}
.mid{flex:1;overflow-y:auto;padding:15px}
.bottom{padding:10px;border-top:1px solid #ddd}
.bar{display:flex;align-items:center;background:#fff;border-radius:30px;padding:6px 14px;max-width:700px;margin:0 auto}
.bar input{flex:1;border:none;outline:none;font-size:16px;padding:6px;background:transparent}
.icon{width:36px;height:36px;border-radius:50%;border:none;background:#eee;font-size:20px;margin-right:6px}
.send{background:#000;color:#fff;width:36px;height:36px;border-radius:50%;border:none;margin-left:6px}
.bubble{padding:12px;border-radius:14px;margin:8px 0;max-width:85%;white-space:pre-wrap;line-height:1.5}
.user{background:#e0e0e0;margin-left:auto}.ai{background:#fff;margin-right:auto;box-shadow:0 1px 2px rgba(0,0,0,0.05)}
.img{max-width:100%;border-radius:10px;margin-top:6px}
#wrap{max-width:700px;margin:0 auto;display:flex;flex-direction:column}
</style></head><body>
<div class="top"><span>SAGESSE - salut {{name}}</span><a href="/logout" style="font-size:12px;text-decoration:none">Déconnexion</a></div>
<div class="mid" id="mid"><div id="wrap"><div class="bubble ai">salut {{name}} 👋</div></div></div>
<div class="bottom"><div class="bar">
<input type="file" id="gallery" accept="image/*" hidden>
<button class="icon" onclick="document.getElementById('gallery').click()">🖼️</button>
<input id="q" placeholder="Ton ordre">
<button class="send" onclick="send()">↑</button>
</div></div>
<script>
let selectedFile=null;
document.getElementById('gallery').addEventListener('change',e=>{
 selectedFile=e.target.files[0];
 let w=document.getElementById('wrap');
 w.innerHTML+=`<div class="bubble user"><img class="img" src="${URL.createObjectURL(selectedFile)}"></div>`;
});
async function send(){
 let i=document.getElementById('q'); let q=i.value.trim();
 if(!q &&!selectedFile) return;
 let w=document.getElementById('wrap');
 if(q) w.innerHTML+=`<div class="bubble user">${q}</div>`;
 let tmp=document.createElement('div'); tmp.className='bubble ai'; tmp.textContent='Sagesse réfléchis...'; w.appendChild(tmp);
 document.getElementById('mid').scrollTop=99999;
 try{
   if(selectedFile){
     let fd=new FormData(); fd.append('file',selectedFile); fd.append('prompt',q);
     let r=await fetch('/modify',{method:'POST',body:fd});
     let blob=await r.blob(); tmp.remove();
     let url=URL.createObjectURL(blob);
     w.innerHTML+=`<div class="bubble ai"><img class="img" src="${url}"><br><a href="${url}" download="result.png">Telecharger</a></div>`;
     selectedFile=null; document.getElementById('gallery').value='';
   }else if(q.toLowerCase().includes('image') || q.toLowerCase().includes('génère') || q.toLowerCase().includes('crée')){
     let r=await fetch('/image?q='+encodeURIComponent(q));
     let d=await r.json(); tmp.remove();
     if(d.url){ w.innerHTML+=`<div class="bubble ai"><img class="img" src="${d.url}"><br>${d.reponse||''}</div>`}
     else{ w.innerHTML+=`<div class="bubble ai">${d.reponse||d.error}</div>`}
   }else{
     let r=await fetch('/ask?q='+encodeURIComponent(q));
     let d=await r.json(); tmp.remove();
     w.innerHTML+=`<div class="bubble ai">${d.reponse}</div>`;
   }
   i.value='';
 }catch(e){tmp.textContent='Erreur: '+e.message}
 document.getElementById('mid').scrollTop=99999;
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')send()})
</script></body></html>
"""

@app.route('/login')
def login_page():
    return render_template_string(LOGIN_HTML)

@app.route('/auth/email', methods=['POST'])
def auth_email():
    data=request.get_json()
    email=data.get('email','').strip().lower()
    nom=data.get('nom','').strip()
    if not email or not nom:
        return jsonify({"ok":False,"error":"Champs manquants"})
    save_user(email, {"nom":nom,"email":email,"method":"email"})
    session['user']={"email":email,"nom":nom}
    return jsonify({"ok":True})

@app.route('/auth/google')
def auth_google():
    # Version simple sans clé Google pour l'instant: on demande juste le nom
    # Si tu veux le vrai Google Login, il faut ajouter GOOGLE_CLIENT_ID dans Render
    # Pour l'instant on simule une connexion Google rapide
    session['user']={"email":"google_user@gmail.com","nom":"Utilisateur Google"}
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/login')

@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    name=session['user'].get('nom','ami')
    return render_template_string(HTML.replace('{{name}}', name))

# --- TON CERVEAU INTELLIGENT INTACT ---
@app.route('/ask')
def ask_route():
    if 'user' not in session: return jsonify({"reponse":"Non connecté"}),401
    q=request.args.get('q','')
    mem=load_memoire(); contexte=""
    if mem:
        for m in mem[-12:]: contexte+=f"User: {m['q']}\nSAGESSE: {m['r']}\n\n"
    prompt_final = f"{SYSTEM_GPT}\n\nHISTORIQUE:\n{contexte}\n\nQUESTION ACTUELLE: {q}\n\nRéponds de façon intelligente, structurée, utile comme GPT-4."
    for modele in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent?key={GEMINI_KEY}"
            donnees = {"contents": [{"parts": [{"text": prompt_final}]}], "systemInstruction": {"parts": [{"text": SYSTEM_GPT}]}, "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096, "topP": 0.95}}
            r=requests.post(url, json=donnees, timeout=40)
            if r.ok:
                j=r.json(); texte=j["candidates"][0]["content"]["parts"][0]["text"]; save_memoire(q, texte); return jsonify({"reponse": texte})
        except: continue
    try:
        import urllib.parse
        url_gpt = f"https://text.pollinations.ai/{urllib.parse.quote(prompt_final)}?model=openai-large&system={urllib.parse.quote(SYSTEM_GPT)}"
        r2=requests.get(url_gpt, timeout=30)
        if r2.ok and len(r2.text)>10: save_memoire(q, r2.text); return jsonify({"reponse": r2.text})
    except: pass
    return jsonify({"reponse": f"Je réfléchis... Tu as dit: {q}"})

@app.route('/image')
def image_route():
    q=request.args.get('q','').replace('Crée une image:','').strip()
    if not q: q="paysage"
    import urllib.parse
    prompt=urllib.parse.quote(q + ", high quality, detailed, 4k")
    img_url=f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true&model=flux&enhance=true"
    return jsonify({"url": img_url, "reponse": f"Image générée: {q}"})

@app.route('/modify', methods=['POST'])
def modify():
    f=request.files.get('file'); prompt=(request.form.get('prompt') or '').lower()
    if not f: return jsonify({"reponse":"Pas de fichier"}),400
    img=Image.open(f.stream).convert("RGBA")
    if "ecrit" in prompt:
        out=img.filter(ImageFilter.MedianFilter(size=5)); buf=io.BytesIO(); out.save(buf, format="PNG"); buf.seek(0); return send_file(buf, mimetype='image/png')
    elif "arriere" in prompt or "fond" in prompt:
        datas=img.getdata(); newData=[]
        for item in datas:
            if item[0]>210 and item[1]>210 and item[2]>210: newData.append((255,255,255,0))
            else: newData.append(item)
        img.putdata(newData); buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return send_file(buf, mimetype='image/png')
    else:
        buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return send_file(buf, mimetype='image/png')

if __name__=="__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0",port=port)
