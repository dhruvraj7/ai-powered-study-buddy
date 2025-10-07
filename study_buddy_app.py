# This file contains the complete AI Study Buddy application using Streamlit.
# It handles the User Interface (UI), session state, real-time data storage (Firestore),
# and the API call to Gemini for content generation.

import streamlit as st
import json
import time # Used for simulating delays and backoff
from typing import List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore, auth

# --- 1. Global Setup (Firebase & Canvas Environment) ---

# Global variables provided by the Canvas environment (used for setup)
APP_ID = st.secrets.get("app_id") or "default-app-id"
FIREBASE_CONFIG = st.secrets.get("firebase_config")
INITIAL_AUTH_TOKEN = st.secrets.get("initial_auth_token")

# Initialize Firebase (runs only once per app session)
@st.cache_resource
def initialize_firebase():
    """Initializes Firebase SDK using secrets."""
    try:
        if not firebase_admin._apps:
            # We use the config provided via Streamlit secrets/environment
            cred_json = json.loads(FIREBASE_CONFIG)
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred)
            
        db = firestore.client()
        return db
    except Exception as e:
        st.error(f"Error initializing Firebase. Check configuration. Details: {e}")
        return None

db = initialize_firebase()

# --- 2. Authentication & User ID Management ---

@st.cache_resource
def authenticate_user():
    """Authenticates the user using the custom token or anonymously."""
    try:
        if INITIAL_AUTH_TOKEN:
            # Sign in with the custom token provided by the Canvas environment
            user = auth.verify_id_token(INITIAL_AUTH_TOKEN)
            return user['uid']
        else:
            # Fallback for local development if token is not available
            st.warning("No initial auth token found. Using a default user ID.")
            return "streamlit-anon-user"
    except Exception as e:
        st.error(f"Authentication failed. Details: {e}")
        return "auth-failed"

USER_ID = authenticate_user()
if USER_ID == "auth-failed":
    st.stop()
    
# Construct the Firestore collection path for the current user's notes
NOTES_COLLECTION_PATH = f"artifacts/{APP_ID}/users/{USER_ID}/study_notes"

# --- 3. Firestore Interaction Functions ---

def save_note(notes_content: str):
    """Saves the current notes to Firestore."""
    if not db or not notes_content.strip():
        st.error("Cannot save empty notes.")
        return

    try:
        doc_ref = db.collection(NOTES_COLLECTION_PATH).document()
        
        doc_ref.set({
            'content': notes_content.strip(),
            'timestamp': firestore.SERVER_TIMESTAMP,
            'title': notes_content.strip()[:50] + ('...' if len(notes_content.strip()) > 50 else ''),
            'user_id': USER_ID
        })
        st.success("Notes saved successfully!")
    except Exception as e:
        st.error(f"Error saving notes: {e}")

# --- 4. Gemini API Interaction (Simulated/Placeholder) ---

@st.cache_data(show_spinner=False) # Cache the result for the current input
def generate_quiz_content(notes_content: str) -> Dict[str, Any]:
    """
    Simulates the call to the Gemini API for structured quiz generation.
    
    In a real Streamlit app running on Streamlit Community Cloud, you would 
    use the google-genai SDK here. Since the environment is simulated, 
    we use a placeholder response structure.
    """
    if not notes_content.strip():
        return {"error": "Notes required for generation."}

    # Simulate API call with a brief delay
    with st.spinner("Generating AI Content..."):
        time.sleep(2) # Simulate network latency

    # --- Actual Gemini API Call Structure (What you would implement) ---
    """
    from google import genai
    client = genai.Client(api_key=st.secrets['GEMINI_API_KEY'])
    
    # ... build user_query and response_schema ...
    
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=user_query,
        config={
            "response_mime_type": "application/json",
            "response_schema": response_schema
        }
    )
    return json.loads(response.text)
    """

    # Placeholder Structured Response
    return {
        "quiz": [
            {"question": "Q1: What is the primary benefit of using Streamlit for this project?", 
             "options": ["A. Full control over CSS", "B. Fast development using only Python", "C. Automated Firebase setup"], 
             "correctAnswer": "B. Fast development using only Python"},
            {"question": "Q2: Where does the saved note data reside?", 
             "options": ["A. Local Storage", "B. Firestore database", "C. An internal Streamlit cache"], 
             "correctAnswer": "B. Firestore database"},
        ],
        "flashcards": [
            {"term": "Streamlit", "definition": "A Python library used to create interactive web applications for data science and machine learning quickly."},
            {"term": "Firestore", "definition": "A flexible, scalable NoSQL cloud database used for storing the user's study notes."},
        ]
    }

# --- 5. UI Components (Display) ---

def display_quiz(quiz_data):
    """Displays the generated quiz and flashcards."""
    if quiz_data.get("error"):
        st.error(quiz_data["error"])
        return

    # Display Quiz Questions
    st.subheader("📝 Multiple Choice Quiz")
    if quiz_data.get("quiz"):
        for i, q in enumerate(quiz_data["quiz"]):
            st.markdown(f"**Question {i+1}:** {q['question']}")
            # Use columns for options for a cleaner look
            cols = st.columns(len(q['options']))
            for col, option in zip(cols, q['options']):
                if col.button(option, key=f"q{i}_opt{option}"):
                    if option == q['correctAnswer']:
                        st.success("Correct!")
                    else:
                        st.error(f"Incorrect. The answer is: {q['correctAnswer']}")
            st.markdown("---")
    
    # Display Flashcards (using Expander for simple visual flip)
    st.subheader("💡 Key Flashcards")
    if quiz_data.get("flashcards"):
        for i, card in enumerate(quiz_data["flashcards"]):
            with st.expander(f"**Term {i+1}:** {card['term']}"):
                st.write(f"**Definition:** {card['definition']}")
                
def display_saved_notes():
    """Fetches and displays the user's saved notes from Firestore."""
    st.subheader("📚 Your Saved Notes")
    
    # Simple list of notes (no real-time listener, just a fresh fetch on load)
    try:
        notes_stream = db.collection(NOTES_COLLECTION_PATH).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        notes_list = [note.to_dict() for note in notes_stream]
        
        if not notes_list:
            st.info("No notes saved yet. Use the area above to paste your study material!")
            return

        # Display saved notes as clickable elements to load them back into the input box
        for note in notes_list:
            if st.button(f"📅 {note['title']} - Load", key=note.get('timestamp').strftime('%Y%m%d%H%M%S')):
                st.session_state.notes_input = note['content']
                st.session_state.active_tab = "Notes & Input"
                st.rerun() # Rerun to update the text area immediately
                
    except Exception as e:
        st.error(f"Error retrieving notes: {e}")

# --- 6. Main Streamlit App Layout ---

def main():
    """Defines the main layout and logic of the Streamlit application."""
    
    st.set_page_config(
        page_title="AI Study Buddy", 
        layout="centered", 
        initial_sidebar_state="auto"
    )

    st.title("🧠 AI-Powered Study Buddy")
    st.markdown("---")
    st.info(f"User ID: `{USER_ID}` (Data saved to Firestore for this ID)")

    # Initialize session state for input and active tab
    if 'notes_input' not in st.session_state:
        st.session_state.notes_input = ""
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Notes & Input"
    if 'quiz_result' not in st.session_state:
        st.session_state.quiz_result = None

    # Tabs for navigation
    tab1, tab2 = st.tabs(["✍️ Notes & Input", "✅ Generated Quiz/Flashcards"])

    with tab1:
        st.header("1. Input Your Study Notes")
        
        # Text Area for Notes
        notes_content = st.text_area(
            "Paste your lecture notes, textbook summaries, or study material here.",
            value=st.session_state.notes_input,
            height=250,
            key="input_area"
        )
        st.session_state.notes_input = notes_content

        col_save, col_generate = st.columns(2)
        
        with col_save:
            if st.button("💾 Save Notes to Firestore", use_container_width=True):
                save_note(notes_content)

        with col_generate:
            if st.button("🚀 Generate Quiz & Flashcards (AI)", use_container_width=True):
                if not notes_content.strip():
                    st.warning("Please enter some notes first.")
                else:
                    # Clear previous result and generate new one
                    st.session_state.quiz_result = generate_quiz_content(notes_content)
                    st.session_state.active_tab = "Generated Quiz/Flashcards"
                    # Rerun to switch tab context
                    st.rerun() 

        st.markdown("---")
        display_saved_notes()


    with tab2:
        st.header("2. Review AI-Generated Content")
        
        if st.session_state.quiz_result:
            display_quiz(st.session_state.quiz_result)
        else:
            st.info("No content generated yet. Go to the 'Notes & Input' tab to start.")


if __name__ == "__main__":
    main()
