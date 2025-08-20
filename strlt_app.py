import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import streamlit.components.v1 as components
import uuid
import time
import numpy as np
import html

# ---------------------------------------------------
# Streamlit chat app with play-on-click + autoplay
# - Play-on-click for each bot message (default ON)
# - Checkbox "Auto-play replies" enables autoplay fallback
# - Client-side visual indicator "Sto leggendo..." while audio plays
# Comments in English throughout
# ---------------------------------------------------

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- SESSION STATE INIT ----------
if "messages" not in st.session_state:
    # messages: list of dicts {id, role, content, audio_b64}
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# Toggle for autoplay (default ON)
if "autoplay" not in st.session_state:
    st.session_state.autoplay = True

# ---------- HELPER: TTS -> base64 ----------
def generate_audio_base64(text: str) -> str:
    """
    Synthesize text to speech using gTTS and return base64-encoded MP3 bytes.
    Keep this function relatively small; gTTS may take time for long texts.
    """
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ---------- PROCESS MESSAGE (send to backend, save audio) ----------
def process_message(user_message: str):
    """
    Send user message to backend, receive bot response, generate audio base64
    and store everything in session_state.messages. We DO NOT play audio server-side.
    """
    if not user_message.strip() or st.session_state.processing:
        return

    st.session_state.processing = True
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

    # Try to synthesize audio; if fails, still save textual response
    audio_b64 = None
    try:
        # remove markdown characters that might confuse TTS
        sanitized = bot_response.replace("*", "").replace("#", "")
        audio_b64 = generate_audio_base64(sanitized)
    except Exception as e:
        # If TTS fails, keep audio_b64 = None and continue
        st.warning(f"TTS generation failed: {e}")

    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "bot",
        "content": bot_response,
        "audio_b64": audio_b64
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💬 Xat amb BatllorIA</h1>
    <h2>L'Intelligència Artificial de la família Batllori</h2>
    <div class="badge">🎉 Festa Major de Sants 2025 🎉</div>
</div>
""", unsafe_allow_html=True)

# ---------- Controls: autoplay toggle ----------
st.checkbox("Auto-play replies", value=st.session_state.autoplay, key="autoplay")

# ---------- WELCOME ----------
if not st.session_state.messages:
    st.markdown("### 🎭 Benvingut a la Festa de Sants! \nPregunta'm qualsevol cosa sobre la festa major del barri.")

# ---------- Render chat messages ----------
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        # user bubble
        st.markdown(f"<div class='chat-bubble-user'>🧑 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
    else:
        # bot bubble (text)
        st.markdown(f"<div class='chat-bubble-bot'>🤖 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)

        # playback controls rendered in an isolated iframe using components.html
        if msg.get("audio_b64"):
            # unique ids for DOM elements
            audio_id = f"audio_{msg['id']}"
            btn_id = f"btn_{msg['id']}"
            status_id = f"status_{msg['id']}"

            # Auto-play preference from session_state
            autoplay_flag = "true" if st.session_state.autoplay else "false"

            # small JS component: play button, "Sto leggendo..." indicator and optional autoplay
            audio_html = f"""
            <div style='margin-top:6px; display:flex; align-items:center; gap:8px;'>
                <button id='{btn_id}' style='border-radius:8px; padding:6px 10px; cursor:pointer;'>▶️ Llegeix</button>
                <span id='{status_id}' style='display:none; color:#666; font-size:0.9em;'>Sto leggendo...</span>
                <audio id='{audio_id}' preload='auto'>
                    <source src='data:audio/mp3;base64,{msg['audio_b64']}' type='audio/mp3'>
                    Your browser does not support the audio element.
                </audio>
            </div>
            <script>
            (function() {{
                const audio = document.getElementById('{audio_id}');
                const btn = document.getElementById('{btn_id}');
                const status = document.getElementById('{status_id}');

                // helper to show/hide status
                function show() {{ status.style.display = 'inline'; }}
                function hide() {{ status.style.display = 'none'; }}

                // play-on-click
                btn.addEventListener('click', function(e) {{
                    try {{
                        show();
                        audio.currentTime = 0;
                        audio.play();
                        btn.disabled = true;
                    }} catch(err) {{ console.warn('Play failed', err); }}
                }});

                audio.addEventListener('play', function() {{ show(); btn.disabled = true; }});
                audio.addEventListener('ended', function() {{ hide(); btn.disabled = false; }});
                audio.addEventListener('pause', function() {{ hide(); btn.disabled = false; }});

                // autoplay fallback: wait a short moment so the component is visible,
                // then start playback if the user enabled autoplay in the Streamlit checkbox.
                if ({autoplay_flag} === true) {{
                    // small timeout to allow the page to render fully
                    setTimeout(function() {{
                        try {{
                            show();
                            audio.currentTime = 0;
                            // attempt to play; browsers may block if autoplay policies
                            const p = audio.play();
                            if (p !== undefined) {{
                                p.then(()=>{{ btn.disabled = true; }}).catch(()=>{{ /* autoplay blocked */ hide(); btn.disabled=false; }});
                            }}
                        }} catch(e) {{ console.warn('Autoplay failed', e); hide(); }}
                    }}, 300);
                }}
            }})();
            </script>
            """

            components.html(audio_html, height=80)
        else:
            # no audio: render a small note
            st.markdown("<div class='small-note'>No audio available for this message.</div>", unsafe_allow_html=True)

# ---------- INPUT FORM ----------
with st.form(key="chat_form", clear_on_submit=True):
    cols = st.columns([4,1])
    with cols[0]:
        user_input = st.text_input("Escriu el teu missatge...", "")
    with cols[1]:
        submitted = st.form_submit_button("📨 Envia", type="primary")

    if submitted and user_input.strip():
        # send message and generate audio in background (server-side)
        process_message(user_input)
        # do NOT call st.rerun() here: we want the page to finish rendering so
        # the client-side audio elements can play without being cut by extra reruns.

# ---------- RESET BUTTON ----------
if st.button("🔄 Reiniciar conversa"):
    if st.session_state.conversation_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
        except Exception:
            pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    # After clearing state, rerun to refresh UI
    st.experimental_rerun()

# ---------- PROCESSING INDICATOR ----------
if st.session_state.processing:
    st.info("🤖 Processant la teva pregunta...")

# ---------- NOTES ----------
st.markdown("\n---\n*Notes:* the audio is stored server-side as base64 and embedded in the page.")
