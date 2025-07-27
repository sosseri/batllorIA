# app/main.py
from fastapi import FastAPI, Request
from app.core import generate_response, get_system_prompt
from typing import Dict, List, Optional
import uuid

app = FastAPI()

# Store conversations in memory (in a production app, use a database)
conversations: Dict[str, List[Dict]] = {}

@app.post("/chat")
async def chat_endpoint(req: Request):
    try:
        body = await req.json()
        user_input = body.get("message", "")
        conversation_id = body.get("conversation_id", None)
        
        if not user_input:
            return {"response": "Cap entrada rebuda."}
        
        # Create a new conversation if needed
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
        
        # Get existing conversation history
        conversation_history = conversations[conversation_id]
        
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})
        
        # Prepare messages for the API with system prompt
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ] + conversation_history
        
        # Generate response
        reply = generate_response(messages)
        
        # Add assistant response to history
        conversation_history.append({"role": "assistant", "content": reply})
        
        # Update the conversation store
        conversations[conversation_id] = conversation_history
        
        return {
            "response": reply,
            "conversation_id": conversation_id
        }
    except Exception as e:
        return {"response": f"Error intern: {str(e)}"}

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation history"""
    if conversation_id in conversations:
        return {"conversation": conversations[conversation_id]}
    return {"error": "Conversa no trobada"}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"success": True}
    return {"error": "Conversa no trobada"}

