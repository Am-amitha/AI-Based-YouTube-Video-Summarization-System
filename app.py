import os
import uuid
import validators
import streamlit as st
import yt_dlp
import whisper
from groq import Groq
from gtts import gTTS

# ================= CONFIG =================
st.set_page_config(page_title="YouTube Summarizer", layout="wide")
st.title("🎥 AI-Based YouTube Video Summarizer")

# ================= GROQ API =================
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= SESSION =================
if "summary" not in st.session_state:
    st.session_state.summary = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None

# ================= LAYOUT =================
left, right = st.columns([1, 3])

# ================= LEFT PANEL =================
with left:

    st.subheader("Controls")

    url = st.text_input("Paste YouTube Link")

    output_lang = st.selectbox(
        "Select Language",
        ["English", "Telugu", "Hindi"]
    )

    length_percent = st.slider(
        "Summary Length (%)",
        10, 100, 40
    )

    generate = st.button("🚀 Generate Summary")

# ================= FUNCTIONS =================

def clean_downloads():
    for f in os.listdir(DOWNLOAD_DIR):
        try:
            os.remove(os.path.join(DOWNLOAD_DIR, f))
        except:
            pass


def download_audio(youtube_url):

    audio_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4().hex}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    return audio_path


@st.cache_resource
def load_model():
    return whisper.load_model("tiny")


def transcribe_audio(audio_path):

    model = load_model()

    result = model.transcribe(audio_path, fp16=False)

    return result["text"]


def summarize_text(text, percent):

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
Summarize the following transcript.

Make summary about {percent}% length.

Use bullet points.

{text[:6000]}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


def translate_summary(summary, lang):

    if lang == "English":
        return summary

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": f"Translate into {lang}"},
            {"role": "user", "content": summary},
        ],
    )

    return response.choices[0].message.content.strip()


def generate_audio(text, lang_code):

    audio_path = os.path.join(DOWNLOAD_DIR, "summary_audio.mp3")

    tts = gTTS(text=text[:3000], lang=lang_code)

    tts.save(audio_path)

    return audio_path


# ================= RIGHT PANEL =================
with right:

    st.subheader("Video & Output")

    if generate:

        if not validators.url(url):
            st.error("Invalid URL")

        else:

            clean_downloads()

            st.video(url)

            with st.spinner("Downloading Audio..."):
                audio = download_audio(url)

            with st.spinner("Transcribing Video..."):
                transcript = transcribe_audio(audio)

            with st.spinner("Generating Summary..."):
                summary = summarize_text(transcript, length_percent)

            with st.spinner("Translating..."):
                final_summary = translate_summary(summary, output_lang)

            st.session_state.summary = final_summary
            st.success("✅ Summary Ready")

    if st.session_state.summary:

        st.markdown("### 📌 Summary")

        st.write(st.session_state.summary)

        lang_map = {"English": "en", "Telugu": "te", "Hindi": "hi"}

        if st.button("🔊 Convert to Audio"):

            with st.spinner("Generating Audio..."):

                audio = generate_audio(
                    st.session_state.summary,
                    lang_map[output_lang]
                )

                st.session_state.audio_path = audio

    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path)
