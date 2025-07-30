import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import streamlit.components.v1 as components
import re
import time
import speech_recognition as sr
import numpy as np
import uuid  # Add the missing uuid import here
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import queue
import threading


def generate_audio_base64_gtts(text):
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode(), "gtts"

def play_audio_gtts(text):
    audio_b64, source = generate_audio_base64_gtts(text)
    st.markdown(f"**Veu utilitzada:** {source}")
    st.markdown(f"**Text llegit:** {text}")
    audio_html = f"""
    <audio autoplay controls>
      <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
    </audio>
    """
    components.html(audio_html, height=80)

# UI
st.set_page_config(page_title="✏️Xat amb Batllori")

#st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligencia Artificial de la familia Batllori")

# Page config
st.set_page_config(page_title="Xat amb Batllori")

# response = requests.post("https://batllori-chat.onrender.com/chat", json={"message": user_input})

# Utils
def split_text_into_sentences(text):
    # More sophisticated sentence splitting to avoid over-splitting
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Combine very short sentences with the next one (if possible)
    result = []
    i = 0
    while i < len(sentences):
        if i < len(sentences) - 1 and len(sentences[i]) < 30:
            result.append(sentences[i] + " " + sentences[i+1])
            i += 2
        else:
            result.append(sentences[i])
            i += 1
    return result

def generate_audio_base64(text):
    tts = gTTS(text=text, lang='ca')
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return base64.b64encode(audio_fp.read()).decode()

def play_audio_sequence(sentences):
    if type(sentences)==list:
        for sentence in sentences:
            audio_b64 = generate_audio_base64(sentence)
            audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """
            components.html(audio_html, height=0)
            # Adjust pause duration: shorter for short sentences, minimal base pause
            pause_duration = len(sentence.split()) * (0.5/(np.mean([len(x) for x in sentence.split()]))*5)
            time.sleep(pause_duration)
    else:
        sentence = sentences
        audio_b64 = generate_audio_base64(sentence)
        audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """
        components.html(audio_html, height=0)
        pause_duration = len(sentence.split()) * 0.5
        time.sleep(pause_duration)
        
    # Clear the input field after audio finishes playing
    st.session_state.temp_speech_input = ""

# local function
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Escoltant... Parla ara!", icon="🧏")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=50)
    try:
        text = recognizer.recognize_google(audio, language="ca-ES")
        st.success(f"🔊 Has dit: \"{text}\"")
        return text
    except sr.UnknownValueError:
        st.error("😕 No t'he entès. Torna-ho a provar.")
    except sr.RequestError:
        st.error("❌ Error en la connexió amb el servei de reconeixement.")
    return ""

# local function
def recognize_long_speech(max_chunks=5):
    recognizer = sr.Recognizer()
    full_text = ""
    placeholder = st.empty()

    with sr.Microphone() as source:
        placeholder.info("🎙️ Calibrant micròfon...", icon="🧏")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        placeholder.info("🎙️ Escoltant... Parla ara!", icon="🧏")

        for i in range(max_chunks):
            try:
                placeholder.info(f"🎙️ Escoltant (segment {i+1}/{max_chunks})... Parla o fes una pausa per acabar", icon="🧏")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                
                text = recognizer.recognize_google(audio, language="ca-ES")
                if text:
                    full_text += " " + text
                    placeholder.info(f"🎙️ Captant: {full_text}", icon="🧏")
                else:
                    # If no text was recognized, we might be done
                    break
                    
            except sr.UnknownValueError:
                # No speech detected, might be a pause
                time.sleep(1)
                if i > 0:  # Only break if we already have some text
                    break
            except sr.WaitTimeoutError:
                # User stopped talking
                break
            except sr.RequestError:
                placeholder.error("❌ Error amb Google API.")
                return ""

    placeholder.empty()
    if full_text:
        st.success(f"🔊 Has dit: \"{full_text.strip()}\"")
    else:
        st.warning("😕 No s'ha captat cap veu.")

    return full_text.strip()

# Trascrivi l'audio in catalano
def recognize_speech_from_bytes(audio_bytes):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_bytes) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language="ca-ES")
    except sr.UnknownValueError:
        st.warning("No s’ha entès el que has dit.")
    except sr.RequestError as e:
        st.error(f"Error Google API: {e}")
    return ""

# Leggi la risposta con gTTS
def speak_text(text):
    tts = gTTS(text=text, lang='ca')
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    b64 = base64.b64encode(audio_fp.read()).decode()
    audio_html = f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    st.components.v1.html(audio_html, height=0)

# Estrai frasi per lettura
def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text.strip())

# Coda per l’audio in arrivo
audio_queue = queue.Queue()

class AudioProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.buffer = BytesIO()
        self.recording = True
        self.sample_rate = 16000

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        pcm = frame.to_ndarray().flatten().astype(np.int16).tobytes()
        audio_queue.put(pcm)
        return frame


# Init states
if "messages" not in st.session_state:
    st.session_state.messages = []
if "temp_speech_input" not in st.session_state:
    st.session_state.temp_speech_input = ""
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "session_key" not in st.session_state:
    # Generate a unique session key to avoid duplicate element keys
    import uuid
    st.session_state.session_key = str(uuid.uuid4())[:8]

# Display chat history
for message in st.session_state.messages:
    st.markdown(f"**{message['role']}:** {message['content']}")

# Layout
col1, col2 = st.columns([10, 1])
with col1:
    # Get current speech input if available
    current_input = st.session_state.temp_speech_input if "temp_speech_input" in st.session_state else ""
    # Use a dynamic key with session_key to avoid duplicates
    input_key = f"input_text_{st.session_state.session_key}"
    user_input = st.text_input("Tu:", key=input_key, value=current_input)
#with col2:
#    # Also use unique key for the button
#    mic_button_key = f"mic_button_{st.session_state.session_key}"
#    if st.button("🎤", key=mic_button_key, help="Prem per parlar"):
#        speech_result = recognize_speech()
#        if speech_result:
#            # Store in temporary variable instead of directly in input_text
#            st.session_state.temp_speech_input = speech_result
#            st.rerun()
with col2:
    # Avvia la registrazione
    webrtc_ctx = webrtc_streamer(
        key="mic",
        audio_receiver_size=1024,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
    )

    
    if webrtc_ctx.state.playing:
        st.info("🎤 Escoltant... parla ara (s’aturarà després de 5s de silenci)", icon="🎧")
    
        def record_and_transcribe():
            audio_data = b""
            silence_threshold = 200  # byte length
            silence_count = 0
    
            while silence_count < 10:
                try:
                    chunk = audio_queue.get(timeout=1)
                    if len(chunk.strip(b"\x00")) < silence_threshold:
                        silence_count += 1
                    else:
                        silence_count = 0
                        audio_data += chunk
                except queue.Empty:
                    break
    
            if audio_data:
                wav_bytes = BytesIO()
                import wave
                wf = wave.open(wav_bytes, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
                wf.close()
                wav_bytes.seek(0)
    
                text = recognize_speech_from_bytes(wav_bytes)
                if text:
                    st.session_state.user_input = text
                    st.experimental_rerun()
    
        threading.Thread(target=record_and_transcribe, daemon=True).start()

# Invio - also use a unique key here
send_button_key = f"send_button_{st.session_state.session_key}"
if st.button("Envia", key=send_button_key) and user_input.strip():
    user_msg = user_input.strip()
    # Add user message to chat history
    st.session_state.messages.append({"role": "Tu", "content": user_msg})
    
    ## API call with conversation ID
    #response = requests.post(
    #    "http://localhost:8000/chat", 
    #    json={
    #        "message": user_msg,
    #        "conversation_id": st.session_state.conversation_id
    #    }
    #)
    
    response = requests.post(
        "https://batllori-chat.onrender.com/chat",
        json={
            "message": user_msg,
            "conversation_id": st.session_state.conversation_id
        }
)

    
    response_data = response.json()
    bot_response = response_data["response"]
    
    # Store the conversation ID
    if "conversation_id" in response_data:
        st.session_state.conversation_id = response_data["conversation_id"]
    
    # Add bot response to chat history
    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})
    
    # Clear input field immediately
    st.session_state.temp_speech_input = ""
    # Also clear the current user_input by forcing a new session key
    st.session_state.session_key = str(uuid.uuid4())[:8]
    
    # Display the latest message
    st.markdown("**Tu:** " + user_msg)
    st.markdown("**Batllori:** " + bot_response)

    ## Use the traditional sentence splitting approach with gTTS
    # sentences = split_text_into_sentences(bot_response)
    # play_audio_sequence(sentences)
    play_audio_sequence(bot_response)

    # Rerun to update the UI and clear the input field
    st.rerun()

# Add a reset button to clear the conversation - with unique key
reset_button_key = f"reset_button_{st.session_state.session_key}"
if st.button("Reiniciar conversa", key=reset_button_key):
    if st.session_state.conversation_id:
        ## Optional: Call delete endpoint to clean up server-side
        # requests.delete(f"http://localhost:8000/conversations/{st.session_state.conversation_id}")
        requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.temp_speech_input = ""


    st.session_state.session_key = str(uuid.uuid4())[:8]    # Generate a new session key to ensure fresh UI elements    st.rerun()
