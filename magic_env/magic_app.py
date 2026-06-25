import os
import streamlit as st
from google import genai
import replicate
import requests
from io import BytesIO
import threading
import time

# Page setup
st.set_page_config(page_title="AI Trick Forge", page_icon="🎩", layout="wide")
st.title("🎩 AI Trick Forge (Powered by Google Gemini)")
st.caption("Type any object, and Gemini will invent a brand new magic trick + video demo instantly!")

# Configure Gemini with your API key (load from environment or secrets)
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    st.error("Missing GENAI_API_KEY environment variable. Rotate any exposed keys and set GENAI_API_KEY in your environment or Streamlit secrets.")
    st.stop()

# Configure Replicate API token
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token

# Initialize the client with the API key
client = genai.Client(api_key=api_key)

# Initialize session state
if "trick_text" not in st.session_state:
    st.session_state.trick_text = None
if "user_idea" not in st.session_state:
    st.session_state.user_idea = None
if "video_url" not in st.session_state:
    st.session_state.video_url = None
if "video_generating" not in st.session_state:
    st.session_state.video_generating = False
if "video_error" not in st.session_state:
    st.session_state.video_error = None

# Select the model
model_id = "gemini-2.5-flash"  # Latest and most capable model

def generate_video_background(user_idea, replicate_token):
    """Generate video in background thread"""
    try:
        if not replicate_token:
            st.session_state.video_error = "❌ Replicate API token not found!"
            return
        
        video_prompt = f"""A professional magician performing a {user_idea} magic trick. 
The trick involves amazing sleight of hand and audience interaction. 
Show the setup, performance, and spectacular reveal. 
Cinematic lighting, professional staging, smooth camera work. 
The magician should be skilled and confident. High quality production.
Keep it engaging and impressive."""
        
        output = replicate.run(
            "minimax/video-01:5aa835260ff7f40f4069c41185f72036accf99e29957bb4a3b3a911f3b6c1912",
            input={
                "prompt": video_prompt,
                "duration": 6,
            },
            wait=True
        )
        
        if output:
            if isinstance(output, list) and len(output) > 0:
                st.session_state.video_url = output[0]
            else:
                st.session_state.video_url = str(output)
        else:
            st.session_state.video_error = "⚠️ Video generation completed but no output received."
            
    except Exception as e:
        error_msg = str(e)
        if "timed out" in error_msg.lower():
            st.session_state.video_error = "📹 Video is still being generated in the background. Refresh page in 3-5 minutes."
        elif "rate limit" in error_msg.lower():
            st.session_state.video_error = "⚠️ Replicate rate limit reached. Try again later."
        elif "not found" in error_msg.lower() or "404" in error_msg:
            st.session_state.video_error = "❌ Video model not found."
        else:
            st.session_state.video_error = f"Error: {error_msg[:100]}"
    
    st.session_state.video_generating = False

# User input
user_idea = st.text_input("What object or idea do you want a trick for?", placeholder="e.g., a napkin, a coin, or a pencil")

if st.button("✨ Invent My Trick + Generate Video"):
    if user_idea:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📖 Generating Trick...")
            trick_placeholder = st.empty()
        
        with col2:
            st.subheader("🎬 Generating Video...")
            video_placeholder = st.empty()
        
        try:
            # Generate trick
            prompt = f"""You are a master magician. Invent a completely original, physically possible magic trick for this item: {user_idea}

Always output using these exact headers:
**Trick Name:**
**Props Needed:**
**The Secret Method:**
**What The Audience Sees:**
**The Magician's Script:**

The trick MUST be physically possible using real-world physics or psychology. No actual magic, no CGI, no superpowers."""
            
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            
            # Store trick
            st.session_state.trick_text = response.text
            st.session_state.user_idea = user_idea
            st.session_state.video_url = None
            st.session_state.video_error = None
            
            # Display trick
            with trick_placeholder.container():
                st.markdown("✅ **Trick generated!**")
                st.markdown(response.text)
            
            # Start video generation in background
            st.session_state.video_generating = True
            video_thread = threading.Thread(
                target=generate_video_background,
                args=(user_idea, replicate_token),
                daemon=True
            )
            video_thread.start()
            
            # Show loading for video
            with video_placeholder.container():
                st.info("⏳ Video generating... (2-5 minutes)")
                st.caption("You can refresh the page or navigate away. The video will appear here when ready.")
                
        except Exception as e:
            trick_placeholder.error(f"Error generating trick: {str(e)}")
    else:
        st.warning("Please type an object or idea first!")

# Display video status if generating or completed
st.divider()

if st.session_state.video_generating:
    st.subheader("🎬 Video Status")
    status_placeholder = st.empty()
    with status_placeholder.container():
        st.info("⏳ Video is being generated in the background...")
        if st.button("🔄 Check Status"):
            st.rerun()

if st.session_state.video_error:
    st.subheader("🎬 Video Status")
    st.error(st.session_state.video_error)

if st.session_state.video_url:
    st.subheader("🎬 Your Demo Video")
    st.success("✅ Video generated successfully!")
    if st.session_state.video_url.startswith("http"):
        st.video(st.session_state.video_url)
    else:
        st.info(f"📹 Video URL: {st.session_state.video_url}")

