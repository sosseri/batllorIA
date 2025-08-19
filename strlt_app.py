import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import time
import uuid

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- INIT STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# ---------- HEADER ----------
st.title("💬 Xat amb BatllorIA")
st.caption("L'Intelligència Artificial de la família Batllori per la Festa Major de Sants 🎉")

# ---------- AUDIO ----------
def generate_audio_base64(text: str) -> str:
    """Generate base64 encoded audio from text"""
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio(text: str):
    """Play audio inline"""
    try:
        b64_audio = generate_audio_base64(text)
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception:
        pass

# ---------- MESSAGE HANDLER ----------
def process_message(user_message: str):
    if not user_message.strip() or st.session_state.processing:
        return
    
    st.session_state.processing = True
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_message.strip()})
    
    # Get bot response
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat", 
            json={
                "message": user_message.strip(),
                "conversation_id": st.session_state.conversation_id
            }, 
            timeout=20
        )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")

        # Clean response (remove think blocks)
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
        
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"
    
    # Add bot message
    st.session_state.messages.append({"role": "bot", "content": bot_response})
    
    # Play audio
    play_audio(bot_response.replace("*", "").replace("#", ""))

    st.session_state.processing = False

# ---------- CHAT HISTORY ----------
with st.container():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"🧑 **Tu:** {msg['content']}")
        else:
            st.markdown(f"🤖 **BatllorIA:** {msg['content']}")

# ---------- INPUT ----------
with st.form(key="chat_form", clear_on_submit=True):
    cols = st.columns([4,1])
    with cols[0]:
        user_input = st.text_input("Escriu aquí la teva pregunta:", "")
    with cols[1]:
        submitted = st.form_submit_button("Envia", type="primary")
    
    if submitted and user_input.strip():
        process_message(user_input)
        st.rerun()

# ---------- RESET ----------
if st.button("🔄 Reiniciar conversa"):
    if st.session_state.conversation_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
        except Exception:
            pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()

# ---------- PROCESSING INDICATOR ----------
if st.session_state.processing:
    st.info("🤖 Processant la teva pregunta...")
