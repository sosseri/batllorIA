import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import requests
from gtts import gTTS
from io import BytesIO
import base64
import uuid
import time
import re

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- INIT STATE ----------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ---------- STYLES ----------
st.markdown("""
    <style>
        .message-container {
            background: #faf7f2;
            border-radius: 1rem;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            position: relative;
        }
        .bot {
            border-left: 4px solid #c07d62;
        }
        .user {
            border-left: 4px solid #6c757d;
            text-align: right;
        }
        .reading-icon {
            position: absolute;
            bottom: 0.5rem;
            right: 0.8rem;
            cursor: pointer;
            font-size: 1.2rem;
        }
        .suggestions {
            margin-top: 2rem;
        }
        .suggestion-btn {
            display: inline-block;
            margin: 0.2rem;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            border: 1px solid #c07d62;
            background: #fff;
            font-size: 0.85rem;
            color: #c07d62;
            cursor: pointer;
        }
        .suggestion-btn:hover {
            background: #c07d62;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- FUNCTIONS ----------
def text_to_speech(text):
    tts = gTTS(text=text, lang="ca")
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    b64 = base64.b64encode(fp.read()).decode()
    return f'<audio autoplay src="data:audio/mp3;base64,{b64}"></audio>'

def query_bot(prompt):
    # Replace with your backend call
    time.sleep(1.2)  # simulate thinking
    return f"Resposta simulada per: {prompt}"

# ---------- DISPLAY MESSAGES ----------
for msg in st.session_state["messages"]:
    role, text = msg["role"], msg["content"]
    with st.container():
        st.markdown(
            f"<div class='message-container {role}'>"
            f"{text}"
            f"<span class='reading-icon' onclick=\"navigator.clipboard.writeText('{text}'); "
            f"var audio = document.createElement('audio'); "
            f"audio.src='/read/{uuid.uuid4()}';\">🔊</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# ---------- USER INPUT ----------
prompt = st.text_input("Escriu la teva pregunta...", key="input")
if st.button("Enviar") and prompt:
    # add user message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    # get bot response
    response = query_bot(prompt)
    # add bot message
    st.session_state["messages"].append({"role": "bot", "content": response})
    st.rerun()

# ---------- SUGGESTED QUESTIONS ----------
st.markdown("<div class='suggestions'>", unsafe_allow_html=True)
st.write("💡 Preguntes suggerides:")
suggestions = [
    "Quin és el tema del carrer Papin?",
    "Qui és la família Batllori?",
    "Quines són les altres vies de la festa?",
    "Què hi ha avui al carrer Papin?",
    "Què hi ha demà al carrer Papin?"
]
cols = st.columns(len(suggestions))
for i, sug in enumerate(suggestions):
    if cols[i].button(sug, key=f"sug_{i}"):
        st.session_state["input"] = sug
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ---------- FOOTNOTE ----------
st.markdown("<p style='font-size:0.8rem; color:gray;'>* Aquest xat és una prova inspirada en la ceràmica</p>", unsafe_allow_html=True)
