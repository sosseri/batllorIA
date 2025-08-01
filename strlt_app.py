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

# Gestione del testo vocale dai query parameters - SOLO UNA VOLTA
params = st.query_params
speech_param = params.get("speech", "")
if speech_param and speech_param != st.session_state.speech_input:
    decoded_speech = urllib.parse.unquote(speech_param)
    st.session_state.speech_input = decoded_speech
    # Pulisci immediatamente i parametri per evitare loop
    st.query_params.clear()

# Mostra cronologia
for msg in st.session_state.messages:
    st.markdown(f"**{msg['role']}:** {msg['content']}")

# Input field
user_input = st.text_input("Tu:", value=st.session_state.speech_input, key="user_input")

# Microfono - usa un key univoco per evitare duplicazioni
mic_key = f"mic_component_{hash(str(st.session_state.messages))}"
components.html(f"""
<div style="margin-top:10px;">
  <button id="mic" style="font-size:1.3em; padding:0.5em 1.5em; cursor:pointer;">🎤 Parla</button>
  <p id="status" style="font-size:1em; font-style:italic; color:#555;"></p>
</div>
<script>
// Evita duplicazione di event listeners
if (!window.micListenerAdded) {{
    window.micListenerAdded = true;
    
    document.getElementById("mic").onclick = function() {{
        const status = document.getElementById("status");
        
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            status.innerText = "⚠️ Riconoscimento vocale non supportato";
            return;
        }}
        
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'ca-ES';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        status.innerText = "🎙️ Escoltant...";
        recognition.start();
        
        recognition.onresult = function(event) {{
            const transcript = event.results[0][0].transcript;
            status.innerText = "🔊 Trascritto: " + transcript;
            
            // Redirect con il testo trascritto
            setTimeout(() => {{
                const currentUrl = window.location.pathname;
                window.location.href = currentUrl + "?speech=" + encodeURIComponent(transcript);
            }}, 1500);
        }};
        
        recognition.onerror = function(event) {{
            status.innerText = "⚠️ Errore: " + event.error;
        }};
        
        recognition.onend = function() {{
            if (!status.innerText.includes("Trascritto")) {{
                status.innerText = "⏹️ Nessun testo rilevato";
            }}
        }};
    }};
}}
</script>
""", height=130, key=mic_key)

# Funzioni audio
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
