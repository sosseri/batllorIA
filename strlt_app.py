import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import uuid
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- INIT STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- STYLES ----------
st.markdown(
    """
    <style>
    .chat-bubble {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 1rem;
        max-width: 80%;
        word-wrap: break-word;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.1);
    }
    .user-bubble {
        background-color: #dbeafe;
        margin-left: auto;
    }
    .bot-bubble {
        background-color: #f1f5f9;
        margin-right: auto;
        position: relative;
    }
    .speak-btn {
        position: absolute;
        bottom: 4px;
        right: 6px;
        font-size: 1rem;
        cursor: pointer;
        color: #2563eb;
    }
    .suggestions {
        margin-top: 2rem;
        font-size: 0.9rem;
        color: #444;
    }
    .suggestions button {
        margin: 0.25rem;
        padding: 0.3rem 0.6rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
        background: #fafafa;
        font-size: 0.85rem;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- HEADER ----------
st.markdown(
    """
    <h1 style="text-align:center; font-family:serif; color:#6b2c2c;">
        🎭 Xat amb BatllorIA
    </h1>
    <p style="text-align:center; color:#444; font-style:italic;">
        Inspirat en les rajoles ceràmiques del carrer Papin
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------- FUNCTIONS ----------
def generate_tts(text):
    try:
        tts = gTTS(text=text, lang="ca")
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        b64 = base64.b64encode(audio_bytes.read()).decode()
        return f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}"></audio>'
    except Exception:
        return None

# ---------- CHAT UI ----------
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        bubble_id = str(uuid.uuid4())
        st.markdown(
            f"""
            <div class='chat-bubble bot-bubble' id='{bubble_id}'>
                {msg['content']}
                <span class='speak-btn' onclick="var audio=document.getElementById('audio-{bubble_id}'); if(audio){{audio.play()}}">🔊</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if "audio" in msg and msg["audio"]:
            st.markdown(f"<audio id='audio-{bubble_id}' src='{msg['audio']}'></audio>", unsafe_allow_html=True)

# ---------- INPUT ----------
user_input = st.chat_input("Escriu la teva pregunta...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Pensant..."):
        try:
            res = requests.post("http://backend:8000/chat", json={"message": user_input})
            bot_response = res.json().get("response", "No he pogut respondre.")
        except Exception as e:
            bot_response = f"❌ Error: {str(e)}"

        # Clean think blocks
        bot_response = re.sub(r"<think.*?</Thinking>", "", bot_response, flags=re.DOTALL)

    # generate TTS
    audio_html = generate_tts(bot_response)

    st.session_state.messages.append({"role": "bot", "content": bot_response, "audio": audio_html})

    st.rerun()

# ---------- SUGGESTED QUESTIONS ----------
st.markdown("<div class='suggestions'><b>Preguntes suggerides:</b></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("Quin és el tema del carrer Papin?"):
        st.session_state.messages.append({"role": "user", "content": "Quin és el tema del carrer Papin?"})
        st.rerun()
    if st.button("Qui és la família Batllori?"):
        st.session_state.messages.append({"role": "user", "content": "Qui és la família Batllori?"})
        st.rerun()
    if st.button("Quines són les altres vies de la festa?"):
        st.session_state.messages.append({"role": "user", "content": "Quines són les altres vies de la festa?"})
        st.rerun()
with col2:
    if st.button("Què hi ha avui al carrer Papin?"):
        st.session_state.messages.append({"role": "user", "content": "Què hi ha avui al carrer Papin?"})
        st.rerun()
    if st.button("Què hi ha demà al carrer Papin?"):
        st.session_state.messages.append({"role": "user", "content": "Què hi ha demà al carrer Papin?"})
        st.rerun()
