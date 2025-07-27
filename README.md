# Batllori Chatbot

Batllori Chatbot is an interactive conversational AI that simulates Francesc Batllori, a member of the historic Batllori family of ceramists from the Sants neighborhood in Barcelona. This application allows users to have a conversation with "Batllori" using text input or speech recognition, and it responds with both text and spoken Catalan.

## Features

- Interactive chat interface built with Streamlit
- Speech recognition for input using Google Speech Recognition API
- Text-to-speech synthesis using gTTS (Google Text-to-Speech) in Catalan
- Conversation history tracking
- Reset conversation functionality
- Natural speech synthesis with sentence splitting for better pacing

## Components

The application consists of two main parts:

1. **Backend API Server** (FastAPI)
   - Handles chat requests and responses
   - Maintains conversation history
   - Communicates with the Groq LLM API for generating responses

2. **Frontend UI** (Streamlit)
   - Provides user interface for chat interaction
   - Handles speech recognition and text-to-speech
   - Displays conversation history

## Setup and Installation

### Prerequisites

- Python 3.10 or later
- Docker (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd batllori_chatbot_chatgpt
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up API keys:
   - Ensure you have a valid Groq API key for the LLM integration

### Running the Application

#### Option 1: Running locally

1. Start the backend server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. Start the Streamlit frontend:
   ```bash
   cd ui
   streamlit run app.py
   ```

#### Option 2: Using Docker

1. Build and run using Docker:
   ```bash
   docker build -t batllori-chatbot .
   docker run -p 8000:8000 batllori-chatbot
   ```

2. Run the Streamlit frontend separately:
   ```bash
   cd ui
   streamlit run app.py
   ```

## Usage

1. Open your browser and go to the URL shown by Streamlit (typically http://localhost:8501)
2. Type your message in the text box or click the microphone button to speak
3. Press the "Envia" button to send your message
4. The AI will respond with text and spoken Catalan
5. Use the "Reiniciar conversa" button to start a new conversation

## Technical Details

### Speech Recognition
- Uses Google's Speech Recognition API through the `SpeechRecognition` package
- Configured specifically for Catalan language

### Text-to-Speech
- Uses Google's Text-to-Speech (gTTS) for generating Catalan speech
- Implements sentence splitting for more natural speech cadence

### Conversation Management
- Maintains conversation history on the server side
- Uses conversation IDs to track separate conversations

## License

[Specify license information]

## Credits

Developed by [Your Name/Organization]

For questions or support, please contact [contact information].
