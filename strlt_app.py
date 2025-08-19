import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import streamlit.components.v1 as components
import uuid
import time



# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- INIT STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
    /* Global */
    body {
        background-color: #fafafa;
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* Header */
    .main-header {
        background: url('https://upload.wikimedia.org/wikipedia/commons/0/0c/Azulejo_pattern.svg');
        background-size: cover;
        background-position: center;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        color: #222;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header h2 {
        margin-top: 0.5rem;
        font-weight: 400;
        color: #444;
    }
    .badge {
        display: inline-block;
        margin-top: 0.8rem;
        padding: 0.3rem 0.8rem;
        background: #ffeed9;
        color: #d35400;
        border-radius: 12px;
        font-size: 0.9rem;
        font-weight: 600;
    }

    /* Chat bubbles */
    .chat-bubble-user {
        background: #e1f5fe;
        padding: 0.7rem 1rem;
        border-radius: 16px;
        margin: 0.4rem 0;
        max-width: 80%;
        align-self: flex-end;
        margin-left: auto;
    }
    .chat-bubble-bot {
        background: #fff3e0;
        padding: 0.7rem 1rem;
        border-radius: 16px;
        margin: 0.4rem 0;
        max-width: 80%;
        align-self: flex-start;
        margin-right: auto;
    }

    /* Input bar */
    .stTextInput>div>div>input {
        border-radius: 20px;
        border: 1px solid #ddd;
        padding: 0.6rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
<div class="main-header">
    <h1>💬 Xat amb BatllorIA</h1>
    <h2>L'Intelligència Artificial de la família Batllori</h2>
    <div class="badge">🎉 Festa Major de Sants 2025 🎉</div>
</div>
""", unsafe_allow_html=True)

# ---------- AUDIO ----------
def generate_audio_base64(text: str) -> str:
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio(text: str):
    """Generate and play audio in Streamlit"""
    try:
        tts = gTTS(text=text, lang='ca')
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        b64_audio = base64.b64encode(buf.read()).decode()

        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
        """
        components.html(audio_html, height=0)
    except Exception as e:
        st.warning(f"No s'ha pogut reproduir l'àudio: {e}")


# ---------- MESSAGE HANDLER ----------
def process_message(user_message: str):
    if not user_message.strip() or st.session_state.processing:
        return
    
    st.session_state.processing = True
    st.session_state.messages.append({"role": "user", "content": user_message.strip()})
    
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

        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"
    
    st.session_state.messages.append({"role": "bot", "content": bot_response})
    play_audio(bot_response.replace("*", "").replace("#", ""))
    st.session_state.processing = False
    
# ---------- WELCOME ----------
if not st.session_state.messages:
    st.markdown("### 🎭 Benvingut a la Festa de Sants! \nPregunta'm qualsevol cosa sobre la festa major del barri.")

# ---------- CHAT ----------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>🧑 {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-bot'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

# ---------- INPUT ----------
with st.form(key="chat_form", clear_on_submit=True):
    cols = st.columns([4,1])
    with cols[0]:
        user_input = st.text_input("Escriu el teu missatge...", "")
    with cols[1]:
        submitted = st.form_submit_button("📨 Envia", type="primary")
    
    if submitted and user_input.strip():
        process_message(user_input)
        time.sleep(max(5, len(user_input.split()) * 0.5))
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

if st.session_state.processing:
    st.info("🤖 Processant la teva pregunta...")
