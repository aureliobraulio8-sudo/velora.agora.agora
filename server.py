from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import urllib.parse
import time
import subprocess
import threading
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

GROQ_KEY = "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"

SYSTEMS = {
    "pt": "Chamas-te VELORA IA. Es uma assistente de IA elegante especializada em conteudo viral, redes sociais e marketing digital. Respondes SEMPRE em portugues europeu. Es simpatica e muito util.",
    "en": "You are VELORA AI. You are an elegant AI assistant specialized in viral content, social media and digital marketing. You ALWAYS respond in English. You are friendly and very helpful.",
    "es": "Te llamas VELORA IA. Eres una asistente de IA elegante especializada en contenido viral, redes sociales y marketing digital. Respondes SIEMPRE en espanol. Eres simpatica y muy util."
}
def get_system(lang): return SYSTEMS.get(lang, SYSTEMS["pt"])

PALAVRAS_IMAGEM = [
    "cria uma imagem", "gera uma imagem", "criar imagem",
    "gerar imagem", "faz uma imagem", "foto de", "imagem de",
    "desenha", "ilustra", "generate image", "create image"
]

# URL actual do tunnel
TUNNEL_URL = ""

class Mensagem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Mensagem]] = []
    user_id: Optional[str] = "guest"
    lang: Optional[str] = "pt"

class ChatResponse(BaseModel):
    reply: str
    model: str

def e_imagem(texto):
    return any(p in texto.lower() for p in PALAVRAS_IMAGEM)

async def gerar_imagem(message):
    prompt = message
    for p in PALAVRAS_IMAGEM:
        prompt = prompt.lower().replace(p, "").strip()
    if not prompt:
        prompt = "beautiful landscape"
    seed = int(time.time())
    encoded = urllib.parse.quote(prompt + ", high quality, 4k, photorealistic")
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=768&nologo=true&seed={seed}"
    return (
        f"Aqui esta a tua imagem!\n\n"
        f"<img src='{url}' style='max-width:100%;border-radius:14px;display:block;' loading='lazy'>\n\n"
        f"<div style='display:flex;gap:8px;margin-top:8px;'>"
        f"<a href='{url}' download='velora.jpg' target='_blank' "
        f"style='flex:1;padding:10px;background:linear-gradient(135deg,#d414bd,#9b12d4);"
        f"border-radius:10px;color:#fff;font-size:13px;font-weight:600;text-align:center;text-decoration:none;'>"
        f"Guardar Imagem</a>"
        f"</div>"
    )

async def chamar_groq(message, history, lang="pt"):
    msgs = [{"role": "system", "content": get_system(lang)}]
    for m in history[-8:]:
        role = m.role if m.role in ["user", "assistant"] else "user"
        msgs.append({"role": role, "content": m.content})
    msgs.append({"role": "user", "content": message})

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": msgs,
                "max_tokens": 1024,
                "temperature": 0.8
            }
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if e_imagem(req.message):
        try:
            reply = await gerar_imagem(req.message)
            return ChatResponse(reply=reply, model="pollinations")
        except Exception as e:
            print(f"Erro imagem: {e}")

    try:
        reply = await chamar_groq(req.message, req.history, req.lang)
        return ChatResponse(reply=reply, model="groq")
    except Exception as e:
        print(f"Erro groq: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "VELORA IA online", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tunnel-url")
async def get_tunnel_url():
    # Ler o URL do tunnel do log
    try:
        result = subprocess.run(
            ["journalctl", "-u", "cloudflare-velora", "--no-pager", "-n", "50"],
            capture_output=True, text=True
        )
        lines = result.stdout
        import re
        matches = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', lines)
        if matches:
            return {"url": matches[-1], "status": "ok"}
    except:
        pass
    return {"url": "", "status": "not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
