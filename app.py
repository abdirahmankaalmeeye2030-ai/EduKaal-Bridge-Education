"""
Streamlit UI for the Refugee & Local Student Education Bridge (EduKaal).

Layout: student intro form on first load, then response area on top
(like a chat history), input box and controls at the bottom.

Flow:
1. On first visit, the student enters a nickname, age range, and
   subjects (session-only — not saved after the tab closes).
2. The student pastes a lesson or uploads a file (PDF, Word, image,
   or plain text).
3. The app sends the lesson to Gemma (via agent.py) and displays an
   explanation, vocabulary table, and quiz questions (MODE 1).
4. When the student submits answers to those questions, the app
   detects a "pending" quiz in session state and sends the previous
   questions + the student's answers back to Gemma, which returns a
   score and feedback (MODE 2).
5. After every submission, the input box is cleared automatically so
   the student can type their next answer without deleting old text
   themselves. Because Streamlit forbids writing to a widget's
   session_state key after that widget has been created in the same
   run, clearing is done via a "clear_input_next_run" flag that is
   checked at the very top of the script, before the text_area widget
   is instantiated.
6. A "New Lesson" button lets the student reset the current lesson
   and quiz state at any time (e.g. to try a different language).
7. Every response is saved to a session-only history list. Students
   can click any past entry in the sidebar to revisit it without a
   new Gemma call. This history does NOT persist after the browser
   tab closes — true cross-visit history would require a database,
   which is intentionally out of scope for now (see README/write-up).

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

# --- Clear the input box from a PREVIOUS run, if flagged ---
if st.session_state.get("clear_input_next_run"):
    st.session_state["main_input"] = ""
    st.session_state["clear_input_next_run"] = False

# --- Tesseract setup (OCR for uploaded photos) ---
WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(WINDOWS_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT_PATH

# --- Light/Dark mode toggle ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode

with st.sidebar:
    st.button(
        "🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode",
        on_click=toggle_theme,
        use_container_width=True,
    )

if st.session_state.dark_mode:
    bg_color, text_color, card_bg, border_color = "#0e1117", "#fafafa", "#1c1f26", "#3a3f4b"
else:
    bg_color, text_color, card_bg, border_color = "#f7f7f9", "#1a1a1a", "#ffffff", "#c9ccd1"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    section[data-testid="stSidebar"] {{ background-color: {card_bg} !important; }}
    section[data-testid="stSidebar"] * {{ color: {text_color} !important; }}
    h1, h2, h3, p, label, .stMarkdown, .stCaption, span {{ color: {text_color} !important; }}
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
    .stTextInput input {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    .stTextArea textarea::placeholder {{ color: {text_color}99 !important; }}
    .stTable table, .stTable th, .stTable td {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}
    div[data-testid="stPopover"] button, section[data-testid="stSidebar"] button {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    ul[data-baseweb="menu"] {{ background-color: {card_bg} !important; }}
    ul[data-baseweb="menu"] li {{ color: {text_color} !important; }}
    hr {{ border-color: {border_color}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

MIME_PDF = "application/pdf"
MIME_TXT = "text/plain"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_IMAGES = ("image/png", "image/jpeg")

st.title("📚 EduKaal")
st.caption("Refugee & Local Student Education Bridge — paste your lesson, learn in your language.")

if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = None

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "history" not in st.session_state:
    st.session_state.history = []

language = st.sidebar.selectbox(
    "Choose your language / Dooro luqaddaada",
    ["Af-Somali", "Kiswahili", "Arabic", "Luganda"],
)

# --- Session history (sidebar) — revisit earlier lessons this visit ---
if st.session_state.history:
    with st.sidebar:
        st.divider()
        st.caption("📜 This session's history")
        for i, entry in enumerate(reversed(st.session_state.history)):
            label = f"{entry['language']}: {entry['preview']}"
            if st.button(label, key=f"history_{i}"):
                st.session_state.last_result = entry["result"]
                st.rerun()

# --- Student profile (session-only — resets when the browser tab closes) ---
if "student_profile" not in st.session_state:
    st.session_state.student_profile = None

if st.session_state.student_profile is None:
    st.subheader("👋 Let's get started")
    st.caption(
        "This just helps the tutor speak to you personally during this visit. "
        "Please don't share your last name or exact location."
    )
    with st.form("profile_form"):
        nickname = st.text_input("First name or nickname")
        age_range = st.selectbox("Age range", ["6-9", "10-12", "13-15", "16-18"])
        subjects = st.multiselect(
            "Subjects you're learning",
            ["Maths", "Science", "Social Studies", "English"],
        )
        submitted = st.form_submit_button("Start Learning")

        if submitted and nickname.strip():
            st.session_state.student_profile = {
                "nickname": nickname.strip(),
                "age_range": age_range,
                "subjects": subjects,
            }
            st.rerun()

    st.stop()

profile = st.session_state.student_profile
st.caption(
    f"👤 {profile['nickname']} · {profile['age_range']} · "
    f"{', '.join(profile['subjects']) or 'no subjects selected'}"
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


# --- RESPONSE AREA (top) — shows the tutor's most recent reply ---
st.divider()
result = st.session_state.last_result

if result is None:
    st.caption("Your lesson explanation, vocabulary, and quiz will appear here.")

elif result["mode"] == "lesson":
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
    st.info("Type your answers in the box below and press the button again.")

elif result["mode"] == "feedback":
    score = result.get("understanding_score")
    if score is not None:
        st.metric("Understanding Score", f"{score}/10")
    st.subheader("💬 Feedback")
    st.write(result["feedback_native"])
    if result.get("retry_suggestion"):
        st.warning(f"Try again: {result['retry_suggestion']}")

else:
    st.error(result["message"])
    with st.expander("Show raw output (for debugging)"):
        st.code(result.get("raw_output", ""))

st.divider()

# --- INPUT AREA (bottom) — like ChatGPT/Claude ---
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
    height=150,
    key="main_input",
)

col_upload, col_submit, col_reset = st.columns([0.15, 0.65, 0.2])

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

with col_reset:
    if st.button("🔄 New Lesson"):
        st.session_state.last_result = None
        st.session_state.pending_questions = None
        st.session_state["_last_upload"] = None
        st.session_state["clear_input_next_run"] = True
        st.rerun()

# --- Send to the tutor, store the response, then clear the box ---
if ask_clicked and student_input.strip():
    with st.spinner("The tutor is thinking..."):
        subjects_text = ", ".join(profile["subjects"]) if profile["subjects"] else "not specified"
        student_context = (
            f"[Student: {profile['nickname']}, age range {profile['age_range']}, "
            f"studying: {subjects_text}]\n\n"
        )

        if st.session_state.pending_questions:
            questions_text = "\n".join(
                f"{i+1}. {q}" for i, q in enumerate(st.session_state.pending_questions)
            )
            message = (
                student_context
                + f"Previous questions:\n{questions_text}\n\n"
                + f"Student's answers:\n{student_input}"
            )
        else:
            message = student_context + student_input

        try:
            new_result = get_tutor_response(message, language)
        except Exception as e:
            st.error(f"Could not reach the tutor: {e}")
            new_result = None

    st.session_state.last_result = new_result
    if new_result and new_result["mode"] == "lesson":
        st.session_state.pending_questions = new_result["evaluation_questions"]
    elif new_result and new_result["mode"] == "feedback":
        st.session_state.pending_questions = None

    if new_result:
        st.session_state.history.append(
            {
                "preview": student_input[:60] + ("..." if len(student_input) > 60 else ""),
                "language": language,
                "result": new_result,
            }
        )

    st.session_state["_last_upload"] = None
    st.session_state["clear_input_next_run"] = True
    st.rerun()