import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import streamlit.components.v1 as components
import uuid
import time
import html

# ---------------------------------------------------
# Streamlit chat app: on-demand TTS when user presses read
# - Audio is generated only when the user clicks the read button
# - A small "speaker" logo (emoji) is shown next to each bot message
# - When pressed the server generates the MP3 and the client plays it (autoplay)
# Comments in English throughout
# ---------------------------------------------------

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- SESSION STATE INIT ----------
if "messages" not in st.session_state:
    # messages: list of dicts {id, role, content, audio_b64 (optional)}
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "play_request" not in st.session_state:
    # Holds message id that the user requested to play
    st.session_state.play_request = None

# ---------- HELPER: TTS -> base64 ----------
def generate_audio_base64(text: str) -> str:
    """
    Synthesize text to speech using gTTS and return base64-encoded MP3 bytes.
    This is called only when the user explicitly requests playback.
    """
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ---------- PROCESS MESSAGE (send to backend, DO NOT generate audio) ----------
def process_message(user_message: str):
    """
    Send user message to backend, receive bot response and store it in session state.
    No audio is generated at this point.
    """
    if not user_message.strip() or st.session_state.processing:
        return

    st.session_state.processing = True

    # append user message
    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": user_message.strip()
    })

    # Call backend
    bot_response = "❌ Error: no response"
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat",
            json={
                "message": user_message.strip(),
                "conversation_id": st.session_state.conversation_id
            },
            timeout=30
        )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")

        # Remove any <think> blocks if present
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"

    # append bot message WITHOUT audio
    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "bot",
        "content": bot_response,
        # audio_b64 will be created only when user presses read
        "audio_b64": None
    })

    st.session_state.processing = False

# ---------- UI: Header and CSS ----------
st.markdown("""
<style>
    body { background-color: #fafafa; font-family: 'Helvetica Neue', sans-serif; }
    .main-header { background: url('https://upload.wikimedia.org/wikipedia/commons/0/0c/Azulejo_pattern.svg'); background-size: cover; background-position: center; border-radius: 16px; padding: 2rem; text-align: center; color: #222; margin-bottom: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header h2 { margin-top: 0.5rem; font-weight: 400; color: #444; }
    .badge { display: inline-block; margin-top: 0.8rem; padding: 0.3rem 0.8rem; background: #ffeed9; color: #d35400; border-radius: 12px; font-size: 0.9rem; font-weight: 600; }
    .chat-bubble-user { background: #e1f5fe; padding: 0.7rem 1rem; border-radius: 16px; margin: 0.4rem 0; max-width: 80%; align-self: flex-end; margin-left: auto; }
    .chat-bubble-bot { background: #fff3e0; padding: 0.7rem 1rem; border-radius: 16px; margin: 0.4rem 0; max-width: 80%; align-self: flex-start; margin-right: auto; }
    .small-note { color: #666; font-size: 0.9rem; }
    .play-button { border: none; background: transparent; cursor: pointer; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💬 Xat amb BatllorIA</h1>
    <h2>L'Intelligència Artificial de la família Batllori</h2>
    <div class="badge">🎉 Festa Major de Sants 2025 🎉</div>
</div>
""", unsafe_allow_html=True)

# ---------- WELCOME ----------
if not st.session_state.messages:
    st.markdown("""### 🎭 Benvingut a la Festa de Sants! 
Pregunta'm qualsevol cosa sobre la festa major del barri.""")

# ---------- Render chat messages ----------
# We render messages first. Each bot message shows a small speaker icon button that the user can press to request audio generation.
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        # user bubble
        st.markdown(f"<div class='chat-bubble-user'>🧑 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
    else:
        # bot bubble (text) + speaker icon
        cols = st.columns([0.95, 0.05])
        with cols[0]:
            st.markdown(f"<div class='chat-bubble-bot'>🤖 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
        with cols[1]:
            # show a speaker/logo button — when pressed, store the play request in session_state
            btn_key = f"play_{msg['id']}"
            if st.button("🔊", key=btn_key, help="Click to synthesize and play this message"):
                st.session_state.play_request = msg['id']

# ---------- If user requested to play a message, generate audio and render player ----------
if st.session_state.play_request:
    play_id = st.session_state.play_request
    # find the message
    target = None
    for m in st.session_state.messages:
        if m['id'] == play_id and m['role'] == 'bot':
            target = m
            break

    if target is None:
        st.warning("Requested message not found.")
        st.session_state.play_request = None
    else:
        # show a small server-side indicator while generating
        with st.spinner('Generating audio...'):
            try:
                sanitized = target['content'].replace('*', '').replace('#', '')
                audio_b64 = generate_audio_base64(sanitized)
                # save audio to the message so next time we can play without re-generating
                target['audio_b64'] = audio_b64
            except Exception as e:
                st.error(f"TTS generation failed: {e}")
                st.session_state.play_request = None
                audio_b64 = None

        if audio_b64:
            # render an iframe that autoplay plays audio and shows "Sto leggendo..." while playing
            audio_element_id = f"audio_{target['id']}"
            status_id = f"status_{target['id']}"
            player_html = f"""
            <div style='display:flex; align-items:center; gap:12px;'>
                <div style='font-size:1.4rem;'>🔊</div>
                <div>
                    <div style='font-size:0.95rem; color:#333'>Playing message</div>
                    <div id='{status_id}' style='color:#666; font-size:0.9rem; display:none;'>Sto leggendo...</div>
                    <audio id='{audio_element_id}' autoplay>
                        <source src='data:audio/mp3;base64,{audio_b64}' type='audio/mp3'>
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
            <script>
            (function() {{
                const audio = document.getElementById('{audio_element_id}');
                const status = document.getElementById('{status_id}');
                function show() {{ status.style.display = 'block'; }}
                function hide() {{ status.style.display = 'none'; }}
                audio.addEventListener('play', function() {{ show(); }});
                audio.addEventListener('ended', function() {{ hide(); }});
                audio.addEventListener('pause', function() {{ hide(); }});
                // safety: show status immediately (some browsers delay play events)
                setTimeout(()=>{{ show(); }}, 50);
            }})();
            </script>
            """
            components.html(player_html, height=120)
            # clear play_request so it doesn't re-run again automatically
            st.session_state.play_request = None

# ---------- INPUT FORM ----------
with st.form(key="chat_form", clear_on_submit=True):
    cols = st.columns([4,1])
    with cols[0]:
        user_input = st.text_input("Escriu el teu missatge...", "")
    with cols[1]:
        submitted = st.form_submit_button("📨 Envia", type="primary")

    if submitted and user_input.strip():
        # send message and do NOT generate audio here
        process_message(user_input)
        # Do not call st.rerun() here: we let Streamlit finish the normal rerun to show the new message

# ---------- RESET BUTTON ----------
if st.button("🔄 Reiniciar conversa"):
    if st.session_state.conversation_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
        except Exception:
            pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.play_request = None
    st.experimental_rerun()

# ---------- PROCESSING INDICATOR ----------
if st.session_state.processing:
    st.info("🤖 Processing your question...")

# ---------- NOTES ----------
st.markdown("
---
*Notes:* audio is synthesized only when you press the speaker icon. The generated MP3 is kept in memory for the session so pressing the icon again will replay without regenerating until the session resets.")
