#!/usr/bin/env python3
"""
VELORA IA - Servidor Backend
VPS: 62.171.171.108
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import urllib.parse

app = FastAPI(title="VELORA IA Backend")

# ── CORS ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Chaves API ────────────────────────────────────
GROQ_KEY   = "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"
GEMINI_KEY = "AQ.Ab8RN6L182WFoWlJFladCDe-xtd4FY7tA2289c4S64Pk9DaDEQ"

# ── Modelos ───────────────────────────────────────
class Mensagem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Mensagem]] = []
    user_id: Optional[str] = "guest"

class ChatResponse(BaseModel):
    reply: str
    model: str

# ── System prompt ─────────────────────────────────
SYSTEM_PROMPT = """Chamas-te VELORA IA. És uma assistente de inteligência artificial elegante, criativa e especializada em:
- Criação de conteúdo viral para TikTok, Instagram e YouTube
- Geração de legendas, frases motivacionais e poesias impactantes
- Estratégias de marketing digital e crescimento nas redes sociais
- Responder qualquer pergunta de forma clara e útil
Respondes SEMPRE em português. És simpática, directa e muito útil."""

# ── Detectar pedido de imagem ─────────────────────
PALAVRAS_IMAGEM = [
    "cria uma imagem", "gera uma imagem", "criar imagem",
    "gerar imagem", "faz uma imagem", "desenha", "ilustra",
    "foto de", "imagem de", "generate image", "create image"
]

def e_pedido_imagem(texto: str) -> bool:
    return any(p in texto.lower() for p in PALAVRAS_IMAGEM)

# ── Gerar imagem com Pollinations ─────────────────
async def gerar_imagem_resposta(message: str) -> str:
    # Extrair o prompt da mensagem
    prompt = message.lower()
    for p in PALAVRAS_IMAGEM:
        prompt = prompt.replace(p, "").strip()
    if not prompt:
        prompt = message

    # Melhorar o prompt com Groq
    try:
        prompt_melhorado = await chamar_groq(
            f"Transforma este pedido num prompt em inglês para geração de imagem de alta qualidade: {prompt}. Responde APENAS com o prompt em inglês, sem explicações.",
            []
        )
    except:
        prompt_melhorado = f"{prompt}, high quality, photorealistic, 4k"

    # Gerar URL da imagem
    import time
    seed = int(time.time())
    url_encoded = urllib.parse.quote(prompt_melhorado)
    img_url = f"https://image.pollinations.ai/prompt/{url_encoded}?width=768&height=768&nologo=true&seed={seed}"

    return f"Aqui está a tua imagem! 🎨\n\n<img src='{img_url}' style='max-width:100%;border-radius:12px;margin-top:8px;' loading='lazy'>\n\n**Prompt usado:** {prompt_melhorado[:100]}..."

# ── Rota principal de chat ────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):

    # Verificar se é pedido de imagem
    if e_pedido_imagem(req.message):
        try:
            reply = await gerar_imagem_resposta(req.message)
            return ChatResponse(reply=reply, model="pollinations")
        except Exception as e:
            print(f"Erro imagem: {e}")

    # Tentar Groq primeiro
    try:
        reply = await chamar_groq(req.message, req.history)
        return ChatResponse(reply=reply, model="groq")
    except Exception as e:
        print(f"Groq falhou: {e}")

    # Fallback Gemini
    try:
        reply = await chamar_gemini(req.message, req.history)
        return ChatResponse(reply=reply, model="gemini")
    except Exception as e:
        print(f"Gemini falhou: {e}")
        raise HTTPException(status_code=500, detail="Erro nas APIs de IA")

# ── Groq ──────────────────────────────────────────
async def chamar_groq(message: str, history: list) -> str:
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-10:]:
        role = m.role if m.role in ["user", "assistant"] else "user"
        mensagens.append({"role": role, "content": m.content})
    mensagens.append({"role": "user", "content": message})

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama3-8b-8192", "messages": mensagens, "max_tokens": 1024, "temperature": 0.8}
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

# ── Gemini ────────────────────────────────────────
async def chamar_gemini(message: str, history: list) -> str:
    contents = []
    for m in history[-10:]:
        role = "user" if m.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.content}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024}
            }
        )
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]

# ── Rotas de teste ────────────────────────────────
@app.get("/")
async def root():
    return {"status": "VELORA IA Backend online", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
