# app/main.py
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, List
import uuid
import groq
import os

# Importa i prompt e la funzione di generazione da app.core
from app.core import (
    generate_response, 
    SYSTEM_PROMPT, 
    SYSTEM_PROMPT_PROGRAMA, 
    SYSTEM_PROMPT_CARRERS
)

# Inizializza il client Groq qui per la classificazione
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("La variabile d'ambiente GROQ_API_KEY non è stata impostata.")
client = groq.Client(api_key=GROQ_API_KEY)

app = FastAPI()

# Store conversations in memory
conversations: Dict[str, List[Dict]] = {}

def get_prompt_category(user_input: str) -> str:
    """
    Classifica l'input dell'utente per determinare quale prompt usare.
    Restituisce 'Programa', 'Carrers', o 'Estàndard'.
    """
    messages = [
        {
            "role": "system",
            "content": """Ets un assistent classificador. Analitza la pregunta de l'usuari i respon NOMÉS amb una de les tres opcions següents, sense text addicional:
- 'Programa': si la pregunta està relacionada amb el programa de la festa, horaris, o activitats.
- 'Carrers': si la pregunta està relacionada amb la decoració d'altres carrers o quins carrers participen.
- 'Estàndard': per a qualsevol altre tema (història, ceràmica, salutacions, etc.). En cas de dubte, tria 'Estàndard'."""
        },
        {
            "role": "user",
            "content": user_input
        }
    ]
    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Un modello veloce per la classificazione
            messages=messages,
            temperature=0.0,
        )
        category = chat_completion.choices[0].message.content.strip().replace("'", "").lower()
        print(f"Input utente: '{user_input}' -> Categoria classificata: '{category}'")
        return category
    except Exception as e:
        print(f"Errore durante la classificazione: {e}")
        return "estàndard" # Default in caso di errore

@app.post("/chat")
async def chat_endpoint(req: Request):
    try:
        body = await req.json()
        user_input = body.get("message", "")
        conversation_id = body.get("conversation_id")

        if not user_input:
            raise HTTPException(status_code=400, detail="Cap entrada rebuda.")

        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []

        conversation_history = conversations[conversation_id]
        conversation_history.append({"role": "user", "content": user_input})

        # 1. Classifica l'input per scegliere il prompt
        category = get_prompt_category(user_input)

        # 2. Seleziona il prompt di sistema corretto
        if category == 'programa':
            system_prompt = SYSTEM_PROMPT_PROGRAMA
        elif category == 'carrers':
            system_prompt = SYSTEM_PROMPT_CARRERS
        else:
            system_prompt = SYSTEM_PROMPT
        
        # 3. Prepara i messaggi per l'API
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        
        # 4. Genera la risposta
        reply = generate_response(messages)
        
        conversation_history.append({"role": "assistant", "content": reply})
        conversations[conversation_id] = conversation_history
        
        return {
            "response": reply,
            "conversation_id": conversation_id
        }
    except Exception as e:
        # Log dell'errore per il debug
        print(f"Errore nell'endpoint /chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error intern: {str(e)}")

# ... (gli altri endpoint rimangono invariati) ...
@app.get("/")
def read_root():
    return {"message": "Hello from Batllori API"}

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id in conversations:
        return {"conversation": conversations[conversation_id]}
    raise HTTPException(status_code=404, detail="Conversa no trobada")

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="Conversa no trobada")
