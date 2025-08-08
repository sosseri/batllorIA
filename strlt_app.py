import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import streamlit.components.v1 as components
import re
import time
import numpy as np
import uuid
import urllib.parse
import os
import groq
from groq import Groq
import tempfile

# Configurazione pagina
st.set_page_config(page_title="Xat amb Batllori", page_icon="💬")

# ---- Init Groq client only once ----
@st.cache_resource
def init_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("🤖 Falta GROQ_API_KEY!")
        return None, False
    client = groq.Client(api_key=api_key)
    try:
        client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hola"}],
            temperature=0.1,
            max_tokens=2
        )
        return client, True
    except Exception as e:
        st.error(f"Error Groq: {e}")
        return None, False

client, is_connected = init_groq_client()
if not is_connected:
    st.stop()

# ---- Title ----
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# ---- Session state ----
for key, default in {
    "messages": [],
    "conversation_id": None,
    "session_key": str(uuid.uuid4())[:8],
    "speech_text": "",
    "auto_send": False,
    "client": client
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---- Speech transcription from URL ----
params = st.query_params
spoken = params.get("spoken_text", "")
spoken = urllib.parse.unquote(spoken) if spoken else ""
if spoken:
    st.session_state.speech_text = spoken
    st.query_params.clear()
    st.session_state.auto_send = True
else:
    st.session_state.auto_send = False

# ---- Chat history ----
for msg in st.session_state.messages:
    st.markdown(f"**{msg['role']}:** {msg['content']}")

# ---- Input field ----
input_key = f"input_text_{st.session_state.session_key}"
user_input = st.text_input("Tu:", key=input_key, value=st.session_state.speech_text)

# ---- Microphone button (always visible) ----
components.html("""
<div style="margin-top:10px;">
  <button id="mic" style="font-size:0.9em; padding:0.2em 0.6em; cursor:pointer;">🎤 Parla</button>
  <p id="debug_text" style="font-size:1em; font-style:italic; color:#555;"></p>
</div>
<script>
  const mic = document.getElementById("mic");
  const debug = document.getElementById("debug_text");
  mic.onclick = () => {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'ca-ES';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.start();
    debug.innerText = "🎙️ Escoltant...";
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      debug.innerText = "🔊 " + transcript;
      setTimeout(() => {
        const currentUrl = window.location.pathname;
        window.location.href = currentUrl + "?spoken_text=" + encodeURIComponent(transcript);
      }, 300);
    };
    recognition.onerror = () => {
      debug.innerText = "⚠️ Error en el reconeixement de veu.";
    };
  };
</script>
""", height=80)

# ---- Audio functions ----
def generate_audio_base64(text):
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio_sequence(sentences):
    if isinstance(sentences, str):
        sentences = re.split(r'(?<=[.!?])\s+', sentences.strip())
    for s in sentences:
        b64 = generate_audio_base64(s)
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        components.html(audio_html, height=0)
        time.sleep(min(5, len(s.split()) * 0.5))

# ---- Send message function ----
def send_message(msg):
    st.session_state.messages.append({"role": "Tu", "content": msg})
    try:
        r = requests.post("https://batllori-chat.onrender.com/chat", json={
            "message": msg,
            "conversation_id": st.session_state.conversation_id
        })
        rj = r.json()
        bot_response = rj.get("response", "❌ Error")
        bot_response = re.sub(r"\s*<think\b[^>]*>.*?</think>\s*", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
        st.session_state.conversation_id = rj.get("conversation_id", None)
    except Exception as e:
        bot_response = f"❌ Error: {e}"
    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})
    st.markdown("**Tu:** " + msg)
    st.markdown("**Batllori:** " + bot_response)
    play_audio_sequence(bot_response)
    st.session_state.speech_text = ""
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()

# ---- Auto-send if speech captured ----
if st.session_state.auto_send and st.session_state.speech_text.strip():
    send_message(st.session_state.speech_text.strip())

# ---- Manual send ----
if st.button("Envia") and user_input.strip():
    send_message(user_input.strip())

# ---- Reset chat ----
if st.button("Reiniciar conversa"):
    try:
        requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
    except:
        pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.speech_text = ""
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()
