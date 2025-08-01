import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import time
import numpy as np
import uuid
import urllib.parse

# Config
st.set_page_config(page_title="Xat amb Batllori", page_icon="🧠")

# Titolo
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# Init state
for key, default in {
    "messages": [],
    "conversation_id": None,
    "speech_input": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Gestione del testo vocale dai query parameters
params = st.query_params
speech_param = params.get("speech", "")
if speech_param and speech_param != st.session_state.speech_input:
    decoded_speech = urllib.parse.unquote(speech_param)
    st.session_state.speech_input = decoded_speech
    st.query_params.clear()

# Mostra cronologia
for msg in st.session_state.messages:
    st.markdown(f"**{msg['role']}:** {msg['content']}")

# Input field
user_input = st.text_input("Tu:", value=st.session_state.speech_input, key="user_input")

# Sezione riconoscimento vocale semplificata
st.markdown("---")
col1, col2 = st.columns([1, 3])

with col1:
    if st.button("🎤 Parla", help="Clicca per attivare il riconoscimento vocale"):
        st.markdown("""
        <script>
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'ca-ES';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            
            recognition.start();
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                const currentUrl = window.location.pathname;
                window.location.href = currentUrl + "?speech=" + encodeURIComponent(transcript);
            };
        } else {
            alert('Riconoscimento vocale non supportato dal browser');
        }
        </script>
        """, unsafe_allow_html=True)

with col2:
    st.info("Clicca 'Parla' e pronuncia la tua frase in catalano. Il testo apparirà automaticamente nel campo sopra.")

# Alternativa manuale
st.markdown("**Alternativa:** Puoi anche digitare direttamente nel campo di testo sopra.")

# Funzioni audio
def generate_audio_base64(text):
    try:
        tts = gTTS(text=text, lang='ca')
        buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        st.error(f"Errore nella generazione audio: {e}")
        return None

def play_audio_sequence(sentences):
    if isinstance(sentences, str):
        sentences = re.split(r'(?<=[.!?])\s+', sentences.strip())
    
    for s in sentences:
        if s.strip():
            b64 = generate_audio_base64(s.strip())
            if b64:
                audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
                st.markdown(audio_html, unsafe_allow_html=True)
                time.sleep(min(5, len(s.split()) * 0.5))

# Invia messaggio
if st.button("Envia") and user_input.strip():
    user_msg = user_input.strip()
    st.session_state.messages.append({"role": "Tu", "content": user_msg})

    try:
        r = requests.post("https://batllori-chat.onrender.com/chat", json={
            "message": user_msg,
            "conversation_id": st.session_state.conversation_id
        })
        rj = r.json()
        bot_response = rj.get("response", "❌ Error")
        st.session_state.conversation_id = rj.get("conversation_id", None)
    except Exception as e:
        bot_response = f"❌ Error: {e}"

    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})
    st.markdown("**Tu:** " + user_msg)
    st.markdown("**Batllori:** " + bot_response)
    
    # Riproduci audio della risposta
    play_audio_sequence(bot_response)

    # Reset del testo vocale
    st.session_state.speech_input = ""
    st.rerun()

# Reset chat
if st.button("Reiniciar conversa"):
    try:
        requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
    except:
        pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.speech_input = ""
    st.rerun()

# Informazioni di debug
with st.expander("Debug Info"):
    st.write("Session State:", st.session_state)
    st.write("Query Params:", dict(st.query_params))
