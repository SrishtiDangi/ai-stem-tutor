import streamlit as st
import requests
import os
import fitz  # PyMuPDF
import random
import time
import speech_recognition as sr
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import json

HISTORY_FILE = "chat_history.json"
BOOKMARK_FILE = "bookmarked_questions.json"

# Load Chat History
if "chat_history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            st.session_state["chat_history"] = json.load(f)
    else:
        st.session_state["chat_history"] = []

# Load Bookmarked Questions
if "bookmarked_questions" not in st.session_state:
    if os.path.exists(BOOKMARK_FILE):
        with open(BOOKMARK_FILE, "r", encoding="utf-8") as f:
            st.session_state["bookmarked_questions"] = json.load(f)
    else:
        st.session_state["bookmarked_questions"] = []

# Save Chat History
with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(st.session_state["chat_history"], f, ensure_ascii=False, indent=2)

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Load API Key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Streamlit App Config
st.set_page_config(page_title="AI STEM Tutor", page_icon="🧠", layout="wide")
st.markdown("""
    <div style='text-align: center; font-size: 90px;'>🤖</div>
    <h1 style='text-align: center;'>AI STEM Tutor</h1>
""", unsafe_allow_html=True)

# ======================= SIDEBAR NAV =======================
section = st.sidebar.radio("📘 Navigation", [
    "🏠 Ask Tutor", "📄 PDF Reader", "🗘 Quiz Section", "📷 Image Doubt", "🔖 Bookmarked Questions"
])

with st.sidebar.expander("🕓 Conversation History"):
    if st.session_state["chat_history"]:
        for i, item in enumerate(reversed(st.session_state["chat_history"]), 1):
            q, a = item["question"], item["answer"]
            st.markdown(f"**Q{i}:** {q}", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 12px; margin-bottom: 10px;'>{a[:100]}...</div>", unsafe_allow_html=True)
    else:
        st.write("No history yet.")

# ======================= 🌙 Dark Mode =======================
dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=False)

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #f0f0f0; }
        h1, h2, h3, label, .stMarkdown, .stTextInput label, .stRadio label {
            color: #ffffff !important;
        }
        .response-box { background-color: #333333; color: #f5f5f5; padding: 1rem; border-radius: 12px; }
        .stButton > button { background-color: #6c63ff; color: white; border-radius: 10px; }
        .stButton > button:hover { background-color: #928fff; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background-color: #f9f9f6; }
        h1, h2, h3, label, .stMarkdown, .stTextInput label, .stRadio label {
            color: #1a1a1a !important;
        }
        .response-box { background-color: #dbeadf; color: #2a2a2a; padding: 1rem; border-radius: 12px; }
        .stButton > button {
            background-color: #ffcaa6;
            color: #2f2f2f;
            border-radius: 10px;
        }
        .stButton > button:hover {
            background-color: #f5ae84;
        }
        </style>
    """, unsafe_allow_html=True)

# ======================= VOICE TO TEXT =======================
def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening... Speak clearly.")
        audio = r.listen(source, phrase_time_limit=5)
    try:
        return r.recognize_google(audio)
    except:
        return "Sorry, I couldn't understand that."




# =============================🔖 Bookmarked Questions Section==============================


if section == "🔖 Bookmarked Questions":
    st.title("🔖 Your Bookmarked Questions")

    if not st.session_state["bookmarked_questions"]:
        st.info("You have no bookmarked questions yet.")
    else:
        for idx, b in enumerate(st.session_state["bookmarked_questions"]):
            q, a = b["question"], b["answer"]
            q_hash = abs(hash(q))  # or use something like uuid.uuid4() if needed
            with st.expander(f"🔖 Q{idx+1}: {q[:80]}"):
                st.markdown(f"**Question:** {q}")
                st.markdown("**Answer:**")
                st.markdown(f"<div class='response-box'>{a}</div>", unsafe_allow_html=True)
                if st.button(f"❌ Unbookmark Q{idx+1}", key=f"unbookmark_{q_hash}"):
                    st.session_state["bookmarked_questions"] = [
                         b for b in st.session_state["bookmarked_questions"] if b["question"] != q
                    ]
                    with open(BOOKMARK_FILE, "w", encoding="utf-8") as f:
                        json.dump(st.session_state["bookmarked_questions"], f, ensure_ascii=False, indent=2)
                    st.success("✅ Bookmark saved to file.")
                    st.rerun()




# ======================= 📄 PDF READER =======================
elif section == "📄 PDF Reader":
    st.title("📄 Ask From Your Notes (PDF)")

    uploaded_file = st.file_uploader("Upload your PDF notes", type="pdf")
    pdf_text = ""

    if uploaded_file is not None:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            pdf_text += page.get_text()

        with st.expander("🧾 Preview Extracted Text"):
            st.write(pdf_text[:2000] + "..." if len(pdf_text) > 2000 else pdf_text)

        pdf_question = st.text_area("💭 Ask something from your PDF notes:")

        if st.button("🔍 Get Answer from Notes"):
            if not pdf_question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Thinking..."):
                    prompt = f"""You are a tutor helping a student. They uploaded these notes:\n{pdf_text[:3000]}\nNow answer this question clearly:\n{pdf_question}"""
                    headers = {
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "model": "llama3-70b-8192",
                        "messages": [{"role": "user", "content": prompt}]
                    }

                    try:
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                            headers=headers, json=data, timeout=15)
                        res.raise_for_status()
                        pdf_answer = res.json()["choices"][0]["message"]["content"]

                        st.markdown("#### 🧾 Answer Based on Your Notes:")
                        st.markdown(f"<div class='response-box'>{pdf_answer}</div>", unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"⚠️ Error: {e}")

# ======================= 📷 IMAGE DOUBT =======================
elif section == "📷 Image Doubt":
    st.title("📷 Click/Upload Image for Doubt")

    uploaded_image = st.file_uploader("Upload an image (screenshot, handwriting, etc.)", type=["png", "jpg", "jpeg"])

    if uploaded_image is not None:
        st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
        image = Image.open(uploaded_image)
        extracted_text = pytesseract.image_to_string(image)

        st.markdown("#### ✨ Extracted Question:")
        st.code(extracted_text.strip())

        if st.button("Ask Tutor from Image"):
            with st.spinner("Thinking..."):
                prompt = f"You are a friendly STEM tutor. Explain this question clearly:\n\n{extracted_text}"
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "llama3-70b-8192",
                    "messages": [{"role": "user", "content": prompt}]
                }
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                        headers=headers, json=data, timeout=15)
                    res.raise_for_status()
                    answer = res.json()["choices"][0]["message"]["content"]
                    st.markdown("#### 🧾 Tutor’s Answer:")
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")

# ==========================Ask Tutor=============================
elif section == "🏠 Ask Tutor":
    st.title("🧠 Ask Your STEM Tutor")
    subject = st.selectbox("📚 Choose your subject", ["Physics", "Math", "Chemistry", "Biology", "Computer Science"])
    if st.button("🎤 Speak My Doubt"):
        spoken = recognize_speech()
        st.session_state["question"] = spoken
        st.success(f"🛣️ You said: {spoken}")
    question = st.text_area("💭 Type or edit your doubt:", value=st.session_state.get("question", ""), height=120)
    if st.button("✨ Ask Tutor"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                prompt = f"You are a helpful and calm {subject} tutor. Explain this clearly:\n\n{question}"
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "llama3-70b-8192",
                    "messages": [{"role": "user", "content": prompt}]
                }
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                        headers=headers, json=data, timeout=15)
                    res.raise_for_status()
                    answer = res.json()["choices"][0]["message"]["content"]
                    st.session_state["answer"] = answer
                    st.session_state["chat_history"].append({"question": question, "answer": answer})
                    st.markdown("#### 🗞 Tutor’s Answer:")
                    st.markdown(f"<div class='response-box'>{answer}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
    if "answer" in st.session_state and st.session_state["answer"].strip():
        if st.button("🔖 Bookmark This Question"):
            st.session_state["bookmarked_questions"].append({
                "question": question,
                "answer": st.session_state["answer"]
            })
            with open(BOOKMARK_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state["bookmarked_questions"], f, ensure_ascii=False, indent=2)
            st.success("✅ Question bookmarked!")

# ======================= QUIZ SECTION =======================
elif section == "🗘 Quiz Section":
    st.title("📝 Auto-Generated Quiz From PDF Notes")
    uploaded_quiz_pdf = st.file_uploader("Upload your notes PDF", type="pdf")
    num_questions = st.number_input("How many questions to generate?", min_value=1, max_value=10, value=3)
    time_per_question = st.number_input("Time per question (in seconds)", min_value=10, max_value=120, value=20)

    if uploaded_quiz_pdf:
        doc = fitz.open(stream=uploaded_quiz_pdf.read(), filetype="pdf")
        content = ""
        for page in doc:
            content += page.get_text()

        with st.expander("📄 Preview Extracted Text"):
            st.write(content[:2000] + "..." if len(content) > 2000 else content)

        if st.button("🧠 Generate Quiz"):
            with st.spinner("Generating MCQs from your content..."):
                prompt = f"""
You are an expert education quiz assistant. Based on this study material, generate exactly {num_questions} MCQs. Each question should follow this format:

Q: What is ...
A) Option A
B) Option B
C) Option C
D) Option D
Answer: B

Here is the theory material:
{content[:3000]}
"""
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "llama3-70b-8192",
                    "messages": [{"role": "user", "content": prompt}]
                }

                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                        headers=headers, json=data, timeout=30)
                    res.raise_for_status()
                    raw_quiz_text = res.json()["choices"][0]["message"]["content"]
                    st.session_state["quiz_data"] = raw_quiz_text.strip().split("Q:")[1:]
                    st.session_state["quiz_index"] = 0
                    st.session_state["quiz_score"] = 0
                    st.session_state["quiz_answers"] = []
                    st.success("✅ Quiz Generated!")
                except Exception as e:
                    st.error(f"Error generating quiz: {e}")

    if "quiz_data" in st.session_state and st.session_state["quiz_index"] < len(st.session_state["quiz_data"]):
        quiz = st.session_state["quiz_data"][st.session_state["quiz_index"]]
        lines = quiz.strip().split("\n")
        question = lines[0]
        options = lines[1:5]
        correct = next((line for line in lines if "Answer:" in line), "Answer: A").split(":")[-1].strip()

        st.markdown(f"### Q{st.session_state['quiz_index'] + 1}: {question}")
        selected = st.radio("Choose an option:", options, key=f"q_{st.session_state['quiz_index']}")

        if "start_time" not in st.session_state:
            st.session_state["start_time"] = time.time()

        time_elapsed = int(time.time() - st.session_state["start_time"])
        remaining = time_per_question - time_elapsed
        if remaining > 0:
            st.info(f"⏰ Time remaining: {remaining} seconds")
        else:
            st.warning("⏰ Time's up! Moving to next question...")
            st.session_state["quiz_answers"].append((question, correct, "(No Answer)"))
            st.session_state["quiz_index"] += 1
            st.session_state.pop("start_time", None)
            st.rerun()

        if st.button("✅ Submit Answer"):
            selected_letter = selected.split(")")[0]
            st.session_state["quiz_answers"].append((question, correct, selected_letter.strip()))
            if selected_letter.strip() == correct:
                st.success("✅ Correct!")
                st.session_state["quiz_score"] += 1
            else:
                st.error(f"❌ Incorrect. Correct answer: {correct}")
            st.session_state["quiz_index"] += 1
            st.session_state.pop("start_time", None)
            st.rerun()

    elif "quiz_data" in st.session_state:
        total = len(st.session_state["quiz_data"])
        score = st.session_state.get("quiz_score", 0)
        st.markdown(f"### 🧠 Your Final Score: {score}/{total}")

        with st.expander("📘 View Solutions"):
            for i, (q, correct, user_ans) in enumerate(st.session_state["quiz_answers"], 1):
                st.markdown(f"**Q{i}:** {q}")
                st.markdown(f"- ✅ Correct Answer: {correct}")
                st.markdown(f"- 📝 Your Answer: {user_ans}")

