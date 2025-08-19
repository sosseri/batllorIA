import streamlit as st
import requests
import re
import uuid
from gtts import gTTS
from io import BytesIO
import base64

st.set_page_config(page_title="BatllorIA", page_icon="🪴", layout="centered")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "speech_text" not in st.session_state:
    st.session_state.speech_text = ""
if "session_key" not in st.session_state:
    st.session_state.session_key = str(uuid.uuid4())[:8]
if "processing" not in st.session_state:
    st.session_state.processing = False


# 🔊 Function to play audio
def play_audio(text: str):
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/tts", 
            json={"text": text, "voice": "alloy", "language": "ca"},
            timeout=20
        )
        if response.status_code == 200:
            audio_bytes = response.content
        else:
            # fallback gTTS
            tts = gTTS(text=text, lang="ca")
            buffer = BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            audio_bytes = buffer.read()
    except Exception:
        # fallback totale
        tts = gTTS(text=text, lang="ca")
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_bytes = buffer.read()

    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
    <audio autoplay="true">
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    st.markdown(md, unsafe_allow_html=True)


# 💬 Function to process message
def process_message(user_message: str):
    if not user_message.strip() or st.session_state.processing:
        return
    
    st.session_state.processing = True

    # append subito il messaggio utente
    st.session_state.messages.append({"role": "user", "content": user_message.strip()})

    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat", 
            json={"message": user_message.strip(), "conversation_id": st.session_state.conversation_id}, 
            timeout=20
        )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")
        # pulizia
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"
    
    # append subito risposta bot
    st.session_state.messages.append({"role": "bot", "content": bot_response})
    st.session_state.processing = False

    # avvia audio
    play_audio(bot_response.replace("*", "").replace("#", ""))


# UI
st.title("🪴 BatllorIA")

# Display messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**Tu:** {msg['content']}")
    else:
        st.markdown(f"**BatllorIA:** {msg['content']}")

# Input
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Escriu el teu missatge:", key=f"user_input_{st.session_state.session_key}")
    submitted = st.form_submit_button("Envia")
    if submitted and user_input.strip():
        process_message(user_input)
        st.rerun()
