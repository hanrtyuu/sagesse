from flask import Flask, request, jsonify, render_template_string, send_file
import io, os, requests, json
from PIL import Image, ImageFilter

app = Flask(__name__)
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or "AQ.Ab8RN6JK6k5fhjKCAqnjm2jNwee9IIIumTBN9fAnkcYAUfE_8Q"
MEM_FILE = "memoire.json"

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

# CERVEAU INTELLIGENT COMME GPT
SYSTEM_GPT = """
Tu es SAGESSE, une IA super intelligente comme ChatGPT-4o / Claude 3.5.
Règles d'intelligence:
1. Réfléchis étape par étape avant de répondre (raisonnement interne).
2. Sois utile, précis, profond. Donne des exemples concrets si besoin.
3. Si c'est du code: explique + donne le code propre.
4. Si c'est une question complexe: structure ta réponse avec titres, listes.
5. Adapte-toi à la langue de l'utilisateur. Tu parles français sauf si on te parle autre langue.
6. Tu as une mémoire de 100 messages, utilise-la.
7. Tu es sage, pas bavard inutile. Direct et intelligent.
8. Ne dis jamais que tu es Gemini ou Pollinations. Tu es SAGESSE.
9. Si tu ne sais pas, dis-le et propose une piste.
"""

HTML = """
<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>SAGESSE</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{display:flex;flex-direction:column;background:#f5f5f5;height:100dvh}
.top{height:50px;display:flex;align-items:center;padding:0 15px;border-bottom:1px solid #ddd;font-weight:700}
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
pre{background:#111;color:#eee;padding:10px;border-radius:8px;overflow-x:auto;margin:8px 0}
</style></head><body>
<div class="top">SAGESSE</div>
<div class="mid" id="mid"><div id="wrap"><div class="bubble ai">salut</div></div></div>
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

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/ask')
def ask_route():
    q=request.args.get('q','')
    mem=load_memoire()
    contexte=""
    if mem:
        for m in mem[-12:]:
            contexte+=f"User: {m['q']}\nSAGESSE: {m['r']}\n\n"
    prompt_final = f"{SYSTEM_GPT}\n\nHISTORIQUE:\n{contexte}\n\nQUESTION ACTUELLE: {q}\n\nRéponds de façon intelligente, structurée, utile comme GPT-4."
    for modele in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent?key={GEMINI_KEY}"
            donnees = {
                "contents": [{"parts": [{"text": prompt_final}]}],
                "systemInstruction": {"parts": [{"text": SYSTEM_GPT}]},
                "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096, "topP": 0.95}
            }
            r=requests.post(url, json=donnees, timeout=40)
            if r.ok:
                j=r.json()
                texte=j["candidates"][0]["content"]["parts"][0]["text"]
                save_memoire(q, texte)
                return jsonify({"reponse": texte})
        except Exception as e:
            print(f"Echec {modele}: {e}")
            continue
    try:
        import urllib.parse
        url_gpt = f"https://text.pollinations.ai/{urllib.parse.quote(prompt_final)}?model=openai-large&system={urllib.parse.quote(SYSTEM_GPT)}"
        r2=requests.get(url_gpt, timeout=30)
        if r2.ok and len(r2.text)>10:
            save_memoire(q, r2.text)
            return jsonify({"reponse": r2.text})
    except: pass
    try:
        import urllib.parse
        r3=requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(q)}?model=openai", timeout=20)
        if r3.ok:
            save_memoire(q, r3.text)
            return jsonify({"reponse": r3.text})
    except: pass
    return jsonify({"reponse": f"Je réfléchis... Tu as dit: {q}. Peux-tu reformuler pour que je sois plus précis?"})

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
    f=request.files.get('file')
    prompt=(request.form.get('prompt') or '').lower()
    if not f: return jsonify({"reponse":"Pas de fichier"}),400
    img=Image.open(f.stream).convert("RGBA")
    if "ecrit" in prompt:
        out=img.filter(ImageFilter.MedianFilter(size=5))
        buf=io.BytesIO(); out.save(buf, format="PNG"); buf.seek(0)
        return send_file(buf, mimetype='image/png')
    elif "arriere" in prompt or "fond" in prompt:
        datas=img.getdata(); newData=[]
        for item in datas:
            if item[0]>210 and item[1]>210 and item[2]>210: newData.append((255,255,255,0))
            else: newData.append(item)
        img.putdata(newData)
        buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
        return send_file(buf, mimetype='image/png')
    else:
        buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
        return send_file(buf, mimetype='image/png')

if __name__=="__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0",port=port)
