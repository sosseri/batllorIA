# app/main.py
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, List
import uuid
import groq
import os
import re #regex

# Importa i prompt e la funzione di generazione da app.core
from app.core import (
    generate_response, 
    SYSTEM_PROMPT, 
    SYSTEM_PROMPT_PROGRAMA, 
    SYSTEM_PROMPT_CARRERS,
    SYSTEM_PROMPT_PROGTOT,
    SYSTEM_PROMPT_BATLLORI,
    SYSTEM_PROMPT_PARTICIPAR,
    SYSTEM_PROMPT_GUARNIT
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
            "content": """Ets un agent de la Batllor-IA, la intel·ligència artificial de la família Batllori, històrics ceramistes del barri de Sants a Barcelona.
Estàs a la Festa Major de Sants al carrer Papin i la gent et fa preguntes.

El teu rol és d’assistent classificador. Analitza la pregunta de l’usuari i respon NOMÉS amb una de les set opcions següents, sense text addicional:

- 'ProgramaTot': si la pregunta està relacionada amb el programa de la festa en carrer Papin o en un altre carrer (horaris o activitats). Si et demanen què hi ha *avui*, *demà* o en algun moment al carrer o a la festa, és aquesta opció
- 'Carrers': si la pregunta està relacionada amb la decoració d’altres carrers o amb quins carrers participen o a quina posició han arrivat els carrers al concurs de guarnit de la festa.
- 'Batllori': si la pregunta està relacionada amb la família Batllori, la seva història o el seu negoci a Sants.
- 'Guarnit': si la pregunta demana un tour al carrer o informació tècnica sobre el guarnit o la decoració del carrer Papin (com està fet, materials, construcció, muntatge, etc.).
- 'Participar': si la pregunta és sobre la comissio de festes o com es pot col·laborar o participar a la comissió de festes del carrer Papin.
- 'Estàndard': per a preguntes sobre la temàtica o la decoració del carrer Papin en general, o qualsevol altre tema (història, ceràmica, salutacions, Sants, etc.). En cas de dubte, tria 'Estàndard'.

⚠️ Nota: si et demanen què hi ha “al carrer” sense especificar quin, sempre es refereixen al carrer Papin.

""" #- 'Programa': si la pregunta està relacionada amb el programa de la festa al carrer Papin (horaris o activitats). Si et demanen què hi ha *avui*, *demà* o en algun moment al carrer Papin, és aquesta opció.
        },
        {
            "role": "user",
            "content": user_input
        }
    ]
    try:
        chat_completion = client.chat.completions.create(
            model="openai/gpt-oss-20B", # Un modello veloce per la classificazione
            messages=messages,
            temperature=0.0,
        )
        category = chat_completion.choices[0].message.content.strip().replace("'", "").lower()
        print(f"Input utente: '{user_input}' -> Categoria classificata: '{category}'")
        return category
    except Exception as e:
        print(f"Errore durante la classificazione: {e}")
        return "estàndard" # Default in caso di errore



def get_prompt_category_with_history(user_input: str, conversation_history: List[Dict]) -> str:
    """
    Classifica l'input de l'usuari per determinar quin prompt usar.
    Ara usa també l'historial de preguntes per donar més context.
    """
    # Past questions (only questions) of user
    past_questions = [
        f"- {msg['content']}"
        for msg in conversation_history
        if msg["role"] == "user"
        ]
    # divide past and current question
    user_message = "Preguntes anteriors (només per context, si cal):\n"
    if past_questions:
        user_message += "\n".join(past_questions[:-1]) + "\n\n"
    else:
        user_message += "(cap)\n\n"
    user_message += f"Pregunta actual (classifica aquesta):\n{user_input}"

    
    messages = [
        {
            "role": "system",
            "content": """Ets un agent de la Batllor-IA, la intel·ligència artificial de la família Batllori, històrics ceramistes del barri de Sants a Barcelona.
                Estàs a la Festa Major de Sants al carrer Papin i la gent et fa preguntes.
                
                El teu rol és d’assistent classificador. Has de classificar NOMÉS l’última pregunta de l’usuari. 
                Les preguntes anteriors només s’han d’utilitzar si són necessàries per entendre referències 
                com “i aquest carrer?”, “i demà?”, “i de Galileu?”. 
                Si la darrera pregunta ja s’entén per si sola, ignora les anteriors.
                Analitza la pregunta de l’usuari i respon NOMÉS amb una de les set opcions següents, sense text addicional:
                
                - 'ProgramaTot': si la pregunta està relacionada amb el programa de la festa (horaris o activitats) en carrer Papin, en un altre carrer o amb el programa general de la festa. Si et demanen què hi ha *avui*, *demà* o en algun moment, per exemple, és aquesta opció.
                - 'Programa': només si la pregunta està relacionada NOMÈS amb el programa de la festa al carrer Papin. Si et demanan en *aquest carrer* o *al carrer* volen dir Papin i es aquesta opcio'.
                - 'Carrers': si la pregunta està relacionada amb la decoració d’altres carrers o amb quins carrers participen.
                - 'Batllori': si la pregunta està relacionada amb la família Batllori, la seva història o el seu negoci a Sants.
                - 'Guarnit': si la pregunta demana un tour al carrer o informació tècnica sobre el guarnit o la decoració del carrer Papin (com està fet, materials, construcció, muntatge, etc.).
                - 'Participar': si la pregunta és sobre la comissio de festes o com es pot col·laborar o participar a la comissió de festes del carrer Papin.
                - 'Estàndard': per a preguntes sobre la temàtica o la decoració del carrer Papin en general, o qualsevol altre tema (història, ceràmica, salutacions, Sants, etc.). En cas de dubte, tria 'Estàndard'.
                
                ⚠️ Nota: si et demanen què hi ha “al carrer” sense especificar quin, sempre es refereixen al carrer Papin.
                
                """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    try:
        chat_completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.0,
        )
        category = chat_completion.choices[0].message.content.strip().replace("'", "").lower()
        print(f"Input usuari: '{user_input}' -> Categoria: '{category}'")
        return category
    except Exception as e:
        print(f"Error durant la classificació: {e}")
        return "estàndard"


@app.post("/chat")
async def chat_endpoint(req: Request):
    try:
        body = await req.json()
        user_input = body.get("message", "")
        conversation_id = body.get("conversation_id")

        if not user_input:
            raise HTTPException(status_code=400, detail="Cap entrada rebuda.")
                                
        if "</think>" in user_input:
            user_input=user_input.split("</think>")[-1].strip().replace('*','').replace('#','')
            
        # Create a new conversation if needed
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []

        conversation_history = conversations[conversation_id]
        
        # Rimuovi il vecchio prompt di sistema se presente e aggiungi il nuovo
        if conversation_history and conversation_history[0]["role"] == "system":
            conversation_history.pop(0)

        # 1. Classifica l\'input per scegliere il prompt
        # category = get_prompt_category(user_input)
        category = get_prompt_category_with_history(user_input, conversation_history)

        # 2. Seleziona il prompt di sistema corretto
        if category == 'programa':
            system_prompt = SYSTEM_PROMPT_PROGRAMA
        elif category == 'carrers':
            system_prompt = SYSTEM_PROMPT_CARRERS
        elif category == 'programatot':
            system_prompt = SYSTEM_PROMPT_PROGTOT
        elif category == 'batllori':
            system_prompt = SYSTEM_PROMPT_BATLLORI
        elif category == 'guarnit':
            system_prompt = SYSTEM_PROMPT_GUARNIT
        elif category == 'participar':
            system_prompt = SYSTEM_PROMPT_PARTICIPAR
        else:
            system_prompt = SYSTEM_PROMPT
        
        # Aggiungi il prompt di sistema all\'inizio della cronologia
        conversation_history.insert(0, {"role": "system", "content": system_prompt})

        # Aggiungi il messaggio dell\'utente alla cronologia
        conversation_history.append({"role": "user", "content": user_input})

        # 3. Prepara i messaggi per l\'API (la cronologia ora include il prompt di sistema)
        messages = conversation_history
        
        # 4. Genera la risposta
        reply = generate_response(messages)
        
        conversation_history.append({"role": "assistant", "content": reply})
        conversations[conversation_id] = conversation_history
        
        return {
            "response": reply,
            "conversation_id": conversation_id
        }
    except Exception as e:
        # Log dell\'errore per il debug
        print(f"Errore nell\'endpoint /chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error intern: {str(e)}")

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

@app.get("/health")
async def health():
    return {"status": "ok"}
    
