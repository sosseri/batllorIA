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
if "waiting" not in st.session_state:
    st.session_state.waiting = False

# ---------- TITLE ----------
st.markdown(
    """
    <h1 style="text-align: center; color: #4B2E2E;">🪴 Xat amb BatllorIA</h1>
    <p style="text-align: center; color: #7A5C5C;">
        Fes la teva pregunta sobre la festa i el barri
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------- FUNCTIONS ----------
def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang="ca")
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_bytes = fp.read()
        return "data:audio/mp3;base64," + base64.b64encode(audio_bytes).decode()
    except Exception as e:
        return None

def query_bot(prompt):
    url = "http://backend:8000/chat"  # FastAPI backend
    response = requests.post(url, json={"prompt": prompt})
    if response.status_code == 200:
        return response.json().get("response", "")
    return "Error: No response from backend."

def clean_response(bot_response):
    return re.sub(r"\s*<think\b[^>]*>.*?</think>\s*", "", bot_response, flags=re.DOTALL | re.IGNORECASE)

# ---------- CHAT DISPLAY ----------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)
        if message["role"] == "assistant" and "audio" in message:
            components.html(
                f"""
                <audio controls autoplay>
                    <source src="{message['audio']}" type="audio/mp3">
                </audio>
                """,
                height=60,
            )

# ---------- INPUT ----------
user_input = st.chat_input("Escriu la teva pregunta...")

# ---------- HANDLE INPUT ----------
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.waiting = True
    st.rerun()

if st.session_state.waiting:
    with st.chat_message("assistant"):
        placeholder = st.empty()
        dots = ""
        for _ in range(3):
            dots += "."
            placeholder.markdown(f"**Pensant{dots}**")
            time.sleep(0.5)

    last_user_message = st.session_state.messages[-1]["content"]
    bot_response = query_bot(last_user_message)
    bot_response = clean_response(bot_response)

    audio_src = text_to_speech(bot_response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": bot_response,
            "audio": audio_src,
        }
    )
    st.session_state.waiting = False
    st.rerun()

# ---------- SUGGESTED QUESTIONS (only if it's the very first user message) ----------
if len(st.session_state.messages) == 0:
    st.markdown("---")
    st.markdown("💡 **Preguntes suggerides:**")
    cols = st.columns(2)
    suggestions = [
        "Quin és el tema del carrer Papin?",
        "Qui és la família Batllori?",
        "Quines són les altres vies de la festa?",
        "Què hi ha avui al carrer Papin?",
        "Què hi ha demà al carrer Papin?",
    ]
    for i, q in enumerate(suggestions):
        if cols[i % 2].button(q):
            st.session_state.messages.append({"role": "user", "content": q})
            st.session_state.waiting = True
            st.rerun()

# ---------- FOOTER ----------
st.markdown("<br><br><p style='text-align:center; color:gray; font-size:12px;'>*Aquest xat és experimental i pot contenir errors*</p>", unsafe_allow_html=True)
