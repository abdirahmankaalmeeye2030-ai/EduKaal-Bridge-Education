"""
Streamlit UI for the Refugee & Local Student Education Bridge.

Flow:
1. Student picks a target language and either pastes a lesson or
   uploads a file (PDF, Word, image, or plain text).
2. The app sends the lesson to Gemma (via agent.py) and displays an
   explanation, vocabulary table, and quiz questions (MODE 1).
3. When the student submits answers to those questions, the app
   detects a "pending" quiz in session state and sends the previous
   questions + the student's answers back to Gemma, which returns a
   score and feedback (MODE 2).

See agent.py for the Gemma API call and JSON parsing, and
system_instruction.txt for the tutor's behavior rules.
"""

import os
import streamlit as st
from pypdf import PdfReader
from docx import Document
from PIL import Image
import pytesseract
from agent import get_tutor_response

st.set_page_config(page_title="EduKaal", page_icon="📚")

# --- Tesseract setup (OCR for uploaded photos) ---
# On Windows, Tesseract isn't on PATH by default, so we point to it
# explicitly. On Mac/Linux (e.g. Streamlit Cloud, `apt install
# tesseract-ocr` via packages.txt), it's already on PATH and this is
# skipped automatically since the path won't exist there.
WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(WINDOWS_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT_PATH

# --- Light/Dark mode toggle ---
# This MUST run before anything reads st.session_state.dark_mode.
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default to dark

def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode

with st.sidebar:
    st.button(
        "🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode",
        on_click=toggle_theme,
        use_container_width=True,
    )

if st.session_state.dark_mode:
    bg_color = "#0e1117"
    text_color = "#fafafa"
    card_bg = "#1c1f26"
    border_color = "#3a3f4b"
else:
    bg_color = "#f7f7f9"
    text_color = "#1a1a1a"
    card_bg = "#ffffff"
    border_color = "#c9ccd1"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    h1, h2, h3, p, label, .stMarkdown, .stCaption, span {{
        color: {text_color} !important;
    }}
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    .stTextArea textarea::placeholder {{
        color: {text_color}99 !important;
    }}
    .stTable table, .stTable th, .stTable td {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}
    div[data-testid="stPopover"] button {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# MIME types we accept from st.file_uploader, named for clarity.
MIME_PDF = "application/pdf"
MIME_TXT = "text/plain"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_IMAGES = ("image/png", "image/jpeg")

st.title("📚 EduKaal")
st.caption("Refugee & Local Student Education Bridge — paste your lesson, learn in your language.")

if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = None

language = st.sidebar.selectbox(
    "Choose your language / Dooro luqaddaada",
    ["Af-Somali", "Kiswahili", "Arabic", "Luganda"],
)


def extract_from_pdf(file) -> str:
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_from_docx(file) -> str:
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_from_image(file) -> str:
    image = Image.open(file)
    return pytesseract.image_to_string(image).strip()


extracted_text = ""
extraction_error = None
uploaded_file = st.session_state.get("_last_upload")

if uploaded_file is not None:
    try:
        if uploaded_file.type == MIME_PDF:
            extracted_text = extract_from_pdf(uploaded_file)
            if not extracted_text:
                extraction_error = (
                    "No text found in this PDF — it may be a scanned image. "
                    "Try uploading it as a photo instead, or paste the text."
                )
        elif uploaded_file.type == MIME_TXT:
            extracted_text = uploaded_file.read().decode("utf-8", errors="ignore").strip()
        elif uploaded_file.type == MIME_DOCX:
            extracted_text = extract_from_docx(uploaded_file)
        elif uploaded_file.type in MIME_IMAGES:
            extracted_text = extract_from_image(uploaded_file)
            if not extracted_text:
                extraction_error = (
                    "No text could be read from this photo. Try a clearer, "
                    "well-lit photo, or paste the text instead."
                )
    except Exception as e:
        extraction_error = f"Could not read this file: {e}"

    if extraction_error:
        st.warning(extraction_error)
    elif extracted_text:
        st.success("File loaded. You can edit the text below before asking the tutor.")

student_input = st.text_area(
    "Paste your lesson text or your answers here:",
    value=extracted_text,
    height=180,
    key="main_input",
)

col_upload, col_submit = st.columns([0.15, 0.85])

with col_upload:
    with st.popover("➕"):
        new_upload = st.file_uploader(
            "Upload lesson",
            type=["pdf", "txt", "docx", "png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="file_uploader",
        )
        st.caption(
            "📌 Works best with text-based lessons. Diagrams and hand-drawn "
            "figures may not extract correctly — type or paste instead."
        )
        st.session_state["_last_upload"] = new_upload

with col_submit:
    ask_clicked = st.button("Ask the Tutor", type="primary")

if ask_clicked and student_input.strip():
    with st.spinner("The tutor is thinking..."):
        if st.session_state.pending_questions:
            questions_text = "\n".join(
                f"{i+1}. {q}" for i, q in enumerate(st.session_state.pending_questions)
            )
            message = (
                f"Previous questions:\n{questions_text}\n\n"
                f"Student's answers:\n{student_input}"
            )
        else:
            message = student_input

        try:
            result = get_tutor_response(message, language)
        except Exception as e:
            st.error(f"Could not reach the tutor: {e}")
            result = None

    if result and result["mode"] == "lesson":
        st.session_state.pending_questions = result["evaluation_questions"]

        st.subheader("📖 Explanation")
        st.write(result["explanation_native"])

        st.subheader("🔤 Vocabulary")
        st.table(
            [
                {
                    "English": v["word"],
                    language: v["word_native"],
                    "Meaning": v["definition"],
                    "Example": v["example_sentence"],
                    f"Example ({language})": v["example_native"],
                }
                for v in result["vocabulary_list"]
            ]
        )

        st.subheader("✍️ Quiz")
        for i, q in enumerate(result["evaluation_questions"], 1):
            st.write(f"**{i}.** {q}")
        st.info("Type your answers in the box above and press the button again.")

    elif result and result["mode"] == "feedback":
        st.session_state.pending_questions = None

        score = result.get("understanding_score")
        if score is not None:
            st.metric("Understanding Score", f"{score}/10")
        st.subheader("💬 Feedback")
        st.write(result["feedback_native"])
        if result.get("retry_suggestion"):
            st.warning(f"Try again: {result['retry_suggestion']}")

    elif result:
        st.error(result["message"])
        with st.expander("Show raw output (for debugging)"):
            st.code(result.get("raw_output", ""))