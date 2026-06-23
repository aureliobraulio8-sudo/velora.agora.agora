// Conexão com o seu servidor local do Velora
const API_URL = "http://localhost:8000/api/chat";

async function enviarMensagemParaIA(textoUsuario) {
    try {
        // 1. Envia a mensagem para o seu server.py
        const resposta = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: textoUsuario,
                provider: "groq" // Altere para "gemini" quando quiser usar o outro modelo
            })
        });

        if (!resposta.ok) throw new Error("Erro na resposta do servidor");

        const dados = await resposta.json();
        
        // 2. Retorna o texto que a IA respondeu
        return dados.response;

    } catch (erro) {
        console.error("Erro ao conectar com o Velora Engine:", erro);
        return "Desculpe, estou com dificuldades para me conectar ao servidor agora.";
    }
}