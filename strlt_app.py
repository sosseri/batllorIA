# streamlit_app_ceramics_ui.py
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

# ------------------------------
# Chat app with:
# - modern ceramics-themed UI
# - animated dots while waiting for response
# - on-demand TTS via speaker icon (audio generated only when pressed)
# - ensures answer waits at least 60 seconds before appearing
# Comments are in English.
# ------------------------------

# Page config
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# --- Session state init ---
if "messages" not in st.session_state:
    # messages: list of dicts {id, role, content, audio_b64 (optional), pending (bool)}
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "play_request" not in st.session_state:
    st.session_state.play_request = None
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "to_process" not in st.session_state:
    # dict: {user_text, placeholder_id, start_time}
    st.session_state.to_process = None

# ---------- Helper: TTS -> base64 ----------
def generate_audio_base64(text: str) -> str:
    """
    Synthesize text to speech using gTTS and return base64-encoded MP3 bytes.
    Called only when the user clicks the speaker button.
    """
    tts = gTTS(text=text, lang="ca")
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ---------- UI styles (ceramics theme) ----------
st.markdown(
    """
    <style>
    /* ceramics-inspired palette: terracotta, cream, glaze */
    :root{
        --terracotta:#c65a2a;
        --cream:#fff7ef;
        --glaze:#2b6b5a;
        --muted:#6b6b6b;
        --tile: url('https://upload.wikimedia.org/wikipedia/commons/0/0c/Azulejo_pattern.svg');
    }

    html, body, [class*="css"]  {
        background: linear-gradient(180deg, #fbfaf8 0%, #fffefc 40%, #fffefc 100%);
        font-family: Inter, "Helvetica Neue", Arial, sans-serif;
    }

    .header {
        background: var(--cream);
        border-radius: 14px;
        padding: 18px;
        display:flex;
        gap:12px;
        align-items:center;
        box-shadow: 0 6px 20px rgba(40,30,20,0.07);
        margin-bottom: 14px;
        border-left: 6px solid var(--terracotta);
    }
    .title { font-size: 20px; margin:0; color:#2f2f2f; font-weight:700; }
    .subtitle { margin:0; font-size:13px; color:var(--muted); }

    .chat-area {
        padding: 14px;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(198,90,50,0.03), rgba(255,255,255,0));
        box-shadow: 0 2px 10px rgba(30,20,10,0.03);
    }

    .bubble-user {
        background: white;
        color:#1f1f1f;
        padding:10px 14px;
        border-radius: 14px;
        border-left: 4px solid #9ec1b1;
        max-width:72%;
        margin-left:auto;
        margin-bottom:8px;
    }
    .bubble-bot {
        background: white;
        color:#1f1f1f;
        padding:10px 14px;
        border-radius: 14px;
        border-right: 4px solid var(--terracotta);
        max-width:72%;
        margin-bottom:8px;
    }
    .meta {
        font-size:12px;
        color:var(--muted);
        margin-top:6px;
    }

    .controls {
        margin-top:12px;
        display:flex;
        gap:8px;
        align-items:center;
    }
    .send-btn {
        background:var(--glaze);
        color: white;
        border: none;
        padding:8px 14px;
        border-radius: 10px;
        cursor:pointer;
    }
    .speaker-btn {
        background: transparent;
        border: none;
        cursor:pointer;
        font-size:18px;
    }

    /* animated dots for waiting */
    .dots {
      display:inline-block;
      width:40px;
      text-align:left;
    }
    .dots span {
      display:inline-block;
      width:6px;
      height:6px;
      margin-right:4px;
      background:var(--terracotta);
      border-radius:50%;
      opacity:0.25;
      animation: bounce 1s infinite linear;
    }
    .dots span:nth-child(2){ animation-delay:0.12s; }
    .dots span:nth-child(3){ animation-delay:0.24s; }
    @keyframes bounce {
      0% { transform: translateY(0); opacity:0.25; }
      50% { transform: translateY(-6px); opacity:1; }
      100% { transform: translateY(0); opacity:0.25; }
    }

    .footer-note {
        color:var(--muted);
        font-size:13px;
        margin-top:14px;
        padding-top:8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown(
    f"""
    <div class="header">
        <div style="font-size:28px; line-height:1;">🫙</div>
        <div>
            <div class="title">Xat amb BatllorIA</div>
            <div class="subtitle">La IA de la festa — ceràmica, ganes i comunitat</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Process queued request BEFORE rendering messages ----------
# If there's a to_process item, perform backend call now (this runs after placeholder was rendered on previous rerun)
if st.session_state.to_process and not st.session_state.processing:
    proc = st.session_state.to_process
    st.session_state.processing = True
    user_text = proc["user_text"]
    placeholder_id = proc["placeholder_id"]
    start_time = time.monotonic()

    # call backend
    bot_response = "❌ Error: no response"
    try:
        # allow enough timeout because we will wait 60s after response if necessary
        resp = requests.post(
            "https://batllori-chat.onrender.com/chat",
            json={"message": user_text, "conversation_id": st.session_state.conversation_id},
            timeout=110,
        )
        data = resp.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {e}"

    # ensure minimum wait of 60 seconds since start_time
    elapsed = time.monotonic() - start_time
    min_wait = 60.0
    if elapsed < min_wait:
        time.sleep(min_wait - elapsed)

    # update the placeholder message in session_state.messages
    updated = False
    for m in st.session_state.messages:
        if m.get("id") == placeholder_id:
            m["content"] = bot_response
            m["pending"] = False
            m["audio_b64"] = None
            updated = True
            break

    # clear processing flags
    st.session_state.to_process = None
    st.session_state.processing = False
    # continue rendering (no immediate rerun needed)

# ---------- Welcome text when empty ----------
if not st.session_state.messages:
    st.markdown(
        """
        <div class="chat-area">
          <div style="padding:8px 14px; border-radius:10px;">
            <strong>🎭 Benvingut a la Festa de Sants!</strong>
            <div class="meta">Pregunta'm qualsevol cosa sobre el programa o activitats.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Render chat area ----------
st.markdown('<div class="chat-area">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='bubble-user'>🧑 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
    else:
        # bot message: if pending True -> show animated dots; otherwise show text + speaker icon
        if msg.get("pending"):
            # show bubble with dots
            st.markdown(
                f"""
                <div class='bubble-bot'>
                    <div style='display:flex; align-items:center; gap:10px;'>
                        <div style='flex:1;'><strong>🤖 Generant resposta</strong> <div class='meta'>Pot trigar una estona</div></div>
                        <div class="dots" title="Esperant..."><span></span><span></span><span></span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # normal bot bubble (text)
            st.markdown(f"<div class='bubble-bot'>🤖 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)

            # speaker button (on-click via callback)
            def make_play_cb(mid=msg["id"]):
                def _cb():
                    st.session_state.play_request = mid
                return _cb

            st.button("🔊", key=f"play_{msg['id']}", on_click=make_play_cb(), help="Click to synthesize and play this message")

st.markdown("</div>", unsafe_allow_html=True)

# ---------- If play_request exists: synthesize audio and display player ----------
if st.session_state.play_request:
    play_id = st.session_state.play_request
    target = None
    for m in st.session_state.messages:
        if m["id"] == play_id and m["role"] == "bot":
            target = m
            break

    if target is None:
        st.warning("Requested message not found.")
        st.session_state.play_request = None
    else:
        # if we already have audio cached, reuse it
        if target.get("audio_b64"):
            audio_b64 = target["audio_b64"]
        else:
            # create audio (server-side) and cache it
            with st.spinner("Generant àudio..."):
                try:
                    sanitized = target["content"].replace("*", "").replace("#", "")
                    audio_b64 = generate_audio_base64(sanitized)
                    target["audio_b64"] = audio_b64
                except Exception as e:
                    st.error(f"TTS generation failed: {e}")
                    st.session_state.play_request = None
                    audio_b64 = None

        if audio_b64:
            audio_element_id = f"audio_{target['id']}"
            status_id = f"status_{target['id']}"
            player_html = f"""
            <div style='display:flex; align-items:center; gap:12px; margin-top:8px;'>
                <div style='font-size:1.4rem;'>🔊</div>
                <div>
                    <div style='font-size:0.95rem; color:#333'>Reproduint resposta</div>
                    <div id='{status_id}' style='color:#666; font-size:0.9rem; display:none;'>Llegint...</div>
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
                setTimeout(()=>{{ show(); }}, 50);
            }})();
            </script>
            """
            components.html(player_html, height=120)
            st.session_state.play_request = None

# ---------- Input row (Send uses callback to create placeholder then rerun) ----------
def send_callback():
    """
    Called when the Send button is clicked.
    Append the user message and a placeholder bot message (pending=True),
    set st.session_state.to_process and then force a rerun so the placeholder shows
    before we execute the heavy backend call on the next run.
    """
    text = st.session_state.user_input.strip()
    if not text:
        return

    # append user message
    st.session_state.messages.append({"id": uuid.uuid4().hex, "role": "user", "content": text})

    # append placeholder bot message (pending)
    placeholder_id = uuid.uuid4().hex
    st.session_state.messages.append(
        {"id": placeholder_id, "role": "bot", "content": "", "audio_b64": None, "pending": True}
    )

    # queue processing to be performed at the start of next run
    st.session_state.to_process = {"user_text": text, "placeholder_id": placeholder_id, "start_time": time.monotonic()}

    # clear input field
    st.session_state.user_input = ""

    # re-render so placeholder is shown immediately
    st.rerun()

# Input UI
st.markdown(
    """
    <div style="margin-top:12px; display:flex; gap:8px; align-items:center;">
    """,
    unsafe_allow_html=True,
)

cols = st.columns([4, 1])
with cols[0]:
    st.text_input("Escriu el teu missatge...", key="user_input", placeholder="Escriu... i prem Envia")
with cols[1]:
    st.button("📨 Envia", key="send_button", on_click=send_callback)

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Reset button (safe callback) ----------
def reset_conversation():
    conv_id = st.session_state.get("conversation_id")
    if conv_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{conv_id}", timeout=5)
        except Exception:
            pass
    # reset keys
    st.session_state["messages"] = []
    st.session_state["conversation_id"] = None
    st.session_state["processing"] = False
    st.session_state["play_request"] = None
    st.session_state["user_input"] = ""
    st.session_state["to_process"] = None
    st.rerun()

st.button("🔄 Reiniciar conversa", on_click=reset_conversation)

# ---------- Processing indicator ----------
if st.session_state.processing:
    st.info("🤖 Processant la teva pregunta...")

# ---------- Footer note (Catalan) ----------
st.markdown(
    "<div class='footer-note'>Clica l'altaveu per llegir les respostes. La primera resposta pot trigar fins a 1 minut.</div>",
    unsafe_allow_html=True,
)
