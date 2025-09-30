import streamlit as st
import google.generativeai as genai
import os

# --- Avatar Constants ---
USER_AVATAR = "⛹️‍♂️"   # emoji for user
BOT_AVATAR = "robot.jpg"  # replace with your bot image path

# --- Configure Gemini API ---
GOOGLE_API_KEY = "AIzaSyCLCH34zcTB-aPrcoM1UJhV7oN0EgbMWb0"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Welcome to the court! 🏀 Select a topic in the sidebar and start chatting!"
        }]
    if "topic" not in st.session_state:
        st.session_state.topic = "Dribbling"


def get_gemini_response(prompt, topic):
    """Send user input + topic context to Gemini with structured instructions"""
    system_instructions = f"""
    You are MikeBot, a basketball training assistant.
    The user selected the topic: {topic}.
    Always give advice that is:
    - Practical and related to basketball or fitness
    - Structured with drills, number of reps, sets, or time
    - Easy for athletes to follow
    Example style:
      "Try 3 sets of 20 left-hand dribbles with cones. 
       Then finish with 2 sets of 1-minute crossover dribbles."
    If the topic is 'Diet', give meal suggestions with portion sizes.
    If the topic is 'Physique Training', give workout sets & reps.
    """
    full_prompt = f"{system_instructions}\nUser: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text


def main():
    st.title("Talk With MikeBot 🤖🏀")

    # Initialize states
    initialize_session_state()

    # Sidebar: topic selection
    st.session_state.topic = st.sidebar.radio(
        "Choose what kind of tips you want:",
        ["Dribbling", "Shooting", "Passing", "Diet", "Physique Training"],
        index=["Dribbling", "Shooting", "Passing", "Diet", "Physique Training"].index(st.session_state.topic)
    )
    st.sidebar.success(f"You selected: {st.session_state.topic}")

    # Display chat history
    for message in st.session_state.messages:
        avatar_icon = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("What's on your mind?"):
        # Show + save user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(prompt)

        # Get Gemini response with strict structure
        response = get_gemini_response(prompt, st.session_state.topic)

        # Show + save bot message
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            st.write(response)


if __name__ == "__main__":
    main()