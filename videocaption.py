import streamlit as st
from google.cloud import speech, texttospeech
import openai
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile
import os

# Set up Streamlit app
st.title("Video Audio Replacement with AI Voice")
st.write("Upload a video, and we'll clean up its audio using AI.")

# File upload for video
uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov"])

if uploaded_file is not None:
    try:
        # Step 1: Extract and transcribe audio from video
        st.write("Processing video...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
            temp_video_file.write(uploaded_file.read())
            temp_video_path = temp_video_file.name
        
        # Load video and extract audio
        video_clip = VideoFileClip(temp_video_path)
        temp_audio_path = tempfile.mktemp(suffix=".wav")
        video_clip.audio.write_audiofile(temp_audio_path)

        # Transcribe audio using Google Speech-to-Text
        st.write("Transcribing audio...")
        client = speech.SpeechClient()
        with open(temp_audio_path, "rb") as audio_file:
            audio_content = audio_file.read()
            
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        transcription = " ".join([result.alternatives[0].transcript for result in response.results])
        
        # Step 2: Clean up transcription with GPT-4
        st.write("Correcting transcription...")
        openai.api_key = "22ec84421ec24230a3638d1b51e3a7dc"
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Correct this transcription: {transcription}"}]
        )
        cleaned_transcription = response.choices[0].message['content']

        # Step 3: Generate AI voice using Google Text-to-Speech
        st.write("Generating new audio...")
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=cleaned_transcription)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Standard-C"  # or "en-US-Wavenet-J" for Journey voice if available
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

        # Save new audio to temp file
        new_audio_path = tempfile.mktemp(suffix=".wav")
        with open(new_audio_path, "wb") as out:
            out.write(response.audio_content)
        
        # Step 4: Replace audio in original video with AI-generated audio
        st.write("Replacing audio in video...")
        new_audio = AudioFileClip(new_audio_path)
        final_video = video_clip.set_audio(new_audio)
        final_video_path = tempfile.mktemp(suffix=".mp4")
        final_video.write_videofile(final_video_path)

        # Step 5: Display or download final video
        st.video(final_video_path)
        st.download_button("Download Video with New Audio", data=open(final_video_path, "rb"), file_name="output_video.mp4")

    except Exception as e:
        st.error(f"An error occurred: {e}")

    finally:
        # Cleanup temporary files to avoid clutter
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if os.path.exists(new_audio_path):
            os.remove(new_audio_path)
        if os.path.exists(final_video_path):
            os.remove(final_video_path)
