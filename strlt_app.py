import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import streamlit.components.v1 as components
import re
import time
import uuid
import urllib.parse
import groq
from groq import Groq

# Page config
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬")

# ---- Init Groq client once per session ----
@st.cache_resource
def init_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("🤖 Falta GROQ_API_KEY!")
        return None, False
    client = groq.Client(api_key=api_key)
    try:
        # warm-up call (very small)
        client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hola"}],
            temperature=0.1,
            max_tokens=2
        )
        return client, True
    except Exception as e:
        st.error(f"Error Groq init: {e}")
        return None, False

client, is_connected = init_groq_client()
if not is_connected:
    st.stop()

# ---- Session state initialization ----
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "speech_input" not in st.session_state:
    st.session_state.speech_input = ""
if "clear_input" not in st.session_state:
    st.session_state.clear_input = False

# ---- Handle speech input from URL parameters ----
params = st.query_params
spoken_text = params.get("spoken_text", "")
if spoken_text:
    spoken_text = urllib.parse.unquote(spoken_text)
    st.session_state.speech_input = spoken_text
    # Clear URL parameters to prevent re-triggering
    st.query_params.clear()
    st.rerun()

# ---- UI Header ----
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# ---- Display chat history ----
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"**Tu:** {content}")
        else:
            st.markdown(f"**BatllorIA:** {content}")

# ---- Audio functions ----
def generate_audio_base64(text: str) -> str:
    """Generate base64 encoded audio from text"""
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio_sequence(text: str):
    """Play audio for text, splitting into sentences"""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    for sentence in sentences:
        if sentence.strip():
            try:
                b64_audio = generate_audio_base64(sentence)
                audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                </audio>
                """
                components.html(audio_html, height=0)
                # Pause between sentences
                pause_time = min(4.0, max(0.6, 0.25 * len(sentence.split())))
                time.sleep(pause_time)
            except Exception:
                continue

# ---- Message processing function ----
def process_message(user_message: str):
    """Process user message and get bot response"""
    if not user_message.strip() or st.session_state.processing:
        return
    
    st.session_state.processing = True
    
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user", 
        "content": user_message.strip()
    })
    
    # Get bot response
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat", 
            json={
                "message": user_message.strip(),
                "conversation_id": st.session_state.conversation_id
            }, 
            timeout=20
        )
        response_data = response.json()
        bot_response = response_data.get("response", "❌ Error de connexió")
        
        # Clean response (remove think blocks)
        bot_response = re.sub(
            r"\s*<think\b[^>]*>.*?<Thinking>
</Thinking>\s*", 
            "", 
            bot_response, 
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Update conversation ID
        st.session_state.conversation_id = response_data.get("conversation_id")
        
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"
    
    # Add bot response to chat history
    st.session_state.messages.append({
        "role": "bot", 
        "content": bot_response
    })
    
    # Play audio response
    try:
        play_audio_sequence([bot_response.replace("*","").replace("#","")])
    except Exception:
        pass  # Continue even if audio fails
    
    # Clear inputs and reset processing state
    st.session_state.speech_input = ""
    st.session_state.clear_input = True
    st.session_state.processing = False
    
    # Rerun to update UI
    st.rerun()

# ---- Input section ----
input_container = st.container()
with input_container:
    input_value = st.session_state.speech_input if st.session_state.speech_input else ""
    if st.session_state.clear_input:
        input_value = ""
        st.session_state.clear_input = False
    
    user_input = st.text_input(
        "Tu:", 
        value=input_value,
        key="user_input_field",
        disabled=st.session_state.processing
    )
    
    # Button row
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        send_clicked = st.button(
            "Envia", 
            disabled=st.session_state.processing or not user_input.strip(),
            type="primary"
        )
    
    with col2:
        reset_clicked = st.button("Reiniciar conversa")
    
    with col3:
        # Microphone button with stable implementation
        mic_html = """
        <div style="margin-top: 8px;">
            <button id="micButton" onclick="startRecognition()" 
                    style="background-color: #ff4b4b; color: white; border: none; 
                           padding: 8px 16px; border-radius: 4px; cursor: pointer; 
                           font-size: 14px;">
                🎤 Parla
            </button>
            <span id="micStatus" style="margin-left: 10px; font-size: 12px; color: #666;"></span>
        </div>
        
        <script>
        function startRecognition() {
            const button = document.getElementById('micButton');
            const status = document.getElementById('micStatus');
            
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                status.textContent = '⚠️ Reconeixement de veu no disponible';
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            recognition.lang = 'ca-ES';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            recognition.continuous = false;
            
            button.disabled = true;
            button.style.backgroundColor = '#666';
            status.textContent = '🎙️ Escoltant...';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                status.textContent = '✅ Text reconegut: ' + transcript;
                
                // Redirect with speech text
                setTimeout(() => {
                    const url = new URL(window.location);
                    url.searchParams.set('spoken_text', encodeURIComponent(transcript));
                    window.location.href = url.toString();
                }, 500);
            };
            
            recognition.onerror = function(event) {
                status.textContent = '⚠️ Error: ' + event.error;
                button.disabled = false;
                button.style.backgroundColor = '#ff4b4b';
            };
            
            recognition.onend = function() {
                button.disabled = false;
                button.style.backgroundColor = '#ff4b4b';
                if (!status.textContent.includes('✅')) {
                    status.textContent = '⏹️ Reconeixement finalitzat';
                }
            };
            
            recognition.start();
        }
        </script>
        """
        components.html(mic_html, height=60)

# ---- Handle button clicks ----
if st.session_state.speech_input and not st.session_state.processing:
    process_message(st.session_state.speech_input)

if send_clicked and user_input.strip():
    process_message(user_input)

if reset_clicked:
    # Clear conversation on server
    if st.session_state.conversation_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
        except Exception:
            pass
    
    # Reset session state
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.speech_input = ""
    st.session_state.clear_input = True
    st.session_state.processing = False
    st.rerun()

# ---- Processing indicator ----
if st.session_state.processing:
    st.info("🤖 Processant la teva pregunta...")
