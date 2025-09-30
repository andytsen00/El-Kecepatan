import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- Avatar Constants ---
USER_AVATAR = "⛹️‍♂️"
BOT_AVATAR = "robot.jpg"  # replace with your bot image path or emoji

# --- Configure Gemini API ---
GOOGLE_API_KEY = st.secrets["API"]
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Welcome to the court! 🏀 Ask me for training tips and I’ll guide you."
        }]


def get_gemini_response(prompt: str) -> str:
    """Keep MikeBot's detailed reply style as before (description + goal etc.)."""
    system_instructions = """
    You are MikeBot, a basketball training assistant.
    Always give advice that is:
    - Practical and related to basketball or fitness
    - Structured with drills, number of reps, sets, or time (if applicable)
    - Easy for athletes to follow

    Provide descriptions and goals for exercises (e.g., why to do it and what to focus on),
    but you may also include specific drill lines like:
      "Between the legs: 5 sets of 50 reps
       Crossovers: 3 sets of 1 minute each"

    Keep the reply coach-like and helpful.
    """
    full_prompt = f"{system_instructions}\nUser: {prompt}"
    try:
        response = model.generate_content(full_prompt)
        # The genai SDK returns .text in earlier code; adapt if your SDK differs.
        return getattr(response, "text", str(response))
    except Exception as e:
        return f"⚠️ Error getting response from Gemini: {e}"


# ---------------------------
# --- Parsing / Summaries ---
# ---------------------------
def extract_drills_from_text(text: str):
    """
    Heuristic parser to extract short drill summaries from a free-form assistant reply.
    Returns list of dicts: {'drill','sets','reps','time','source_snippet'}
    """
    text = text.replace("\r", "\n")
    # Find candidate sentences/lines that mention sets/reps/min/sec or numeric patterns
    candidates = []

    # 1) break into sentences by punctuation and newlines, keep those that include keywords or numbers
    raw_sentences = re.split(r'[\n\.]\s*', text)
    for s in raw_sentences:
        if not s.strip():
            continue
        if re.search(r'\b(set|sets|rep|reps|min|minute|sec|second|time)\b', s, flags=re.I) or re.search(r'\d', s):
            candidates.append(s.strip())

    # 2) if no candidates, try to capture any short lines following a colon (e.g., "Between the legs: ...")
    if not candidates:
        colon_lines = re.findall(r'([^:\n]+):\s*([^\n]+)', text)
        for left, right in colon_lines:
            candidates.append(f"{left.strip()}: {right.strip()}")

    results = []
    for c in candidates:
        line = c.strip()

        # remove leading helper words
        line_clean = re.sub(r'^(Try|Then|Finish with|Perform|Do|Start with|Begin with|Continue with)\b[:,]?\s*', '', line, flags=re.I)

        # find sets
        sets_m = re.search(r'(\d+)\s*(?:sets?)\b', line_clean, flags=re.I)
        sets_val = sets_m.group(1) if sets_m else ""

        # find time (e.g., "1 minute", "90 sec", "1-min", "1-minute")
        time_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(\d+(?:\.\d+)?)?\s*(minutes?|minute|mins?|min|seconds?|second|sec)\b', line_clean, flags=re.I)
        time_val = ""
        if time_m:
            if time_m.group(2):
                time_val = f"{time_m.group(1)}-{time_m.group(2)} {time_m.group(3)}"
            else:
                time_val = f"{time_m.group(1)} {time_m.group(3)}"

        # find reps (range or single)
        reps_range_m = re.search(r'(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:reps?)?', line_clean, flags=re.I)
        reps_single_m = re.search(r'(\d+)\s*(?:reps?)\b', line_clean, flags=re.I)

        reps_val = ""
        if reps_range_m:
            reps_val = f"{reps_range_m.group(1)}-{reps_range_m.group(2)}"
        elif reps_single_m:
            # ensure this isn't capturing the sets number (if sets were earlier in string)
            # prefer a reps number that appears after the 'sets' keyword when both present
            if sets_m:
                # find all numeric occurrences and pick one after 'sets' if possible
                idx_sets_end = sets_m.end()
                later_num = re.search(r'(\d+)', line_clean[idx_sets_end:])
                if later_num:
                    reps_val = later_num.group(1)
                else:
                    reps_val = reps_single_m.group(1)
            else:
                reps_val = reps_single_m.group(1)
        else:
            # try pattern 'sets of 20' (e.g., "5 sets of 20 crossovers")
            m_of = re.search(r'(?:sets?\s*(?:of)?)\s*(\d+)\b', line_clean, flags=re.I)
            if sets_m and m_of:
                reps_val = m_of.group(1)

        # attempt to extract a short drill name
        if ":" in line_clean:
            drill_name = line_clean.split(":", 1)[0].strip()
        else:
            # remove numbers/units and filler words to isolate a short name
            temp = re.sub(r'\b\d+(?:\s*-\s*\d+)?\b', '', line_clean)  # remove numbers
            temp = re.sub(r'\b(reps?|sets?|minutes?|minute|mins?|min|seconds?|sec|each|per|side|of|for|with|and|the|a|an|x)\b', ' ', temp, flags=re.I)
            temp = re.sub(r'[,:;\-\(\)\.\[\]]', ' ', temp)
            temp = re.sub(r'\s+', ' ', temp).strip()
            # pick a compact substring (first 6 words)
            words = temp.split()
            drill_name = " ".join(words[:6]).strip().title() if words else ""

        # If all extracted fields are empty, skip unless the line contains digits (to prevent false positives)
        if not (drill_name or sets_val or reps_val or time_val):
            continue

        # Normalize small results
        drill_name = drill_name or "Drill"
        results.append({
            "drill": drill_name,
            "sets": sets_val,
            "reps": reps_val,
            "time": time_val,
            "source": line  # short snippet to trace back
        })

    return results


def build_summary_from_messages(messages):
    """Flatten parsed drills from all assistant messages (except the initial welcome)."""
    all_drills = []
    for idx, m in enumerate(messages):
        if m["role"] != "assistant":
            continue
        if "Welcome" in m["content"] and idx == 0:
            continue
        drills = extract_drills_from_text(m["content"])
        # attach message index so we can label Tip #
        for d in drills:
            d["from_message_index"] = idx
            all_drills.append(d)
    return all_drills


# ---------------------------
# --- Streamlit UI / App ---
# ---------------------------
def main():
    st.set_page_config(page_title="MikeBot — Basketball Trainer", layout="wide")
    st.title("Talk With MikeBot 🤖🏀")
    initialize_session_state()

    # Sidebar: compact summary of drills parsed from MikeBot replies
    st.sidebar.header("📋 Training Summary (extracted)")

    drills = build_summary_from_messages(st.session_state.messages)

    if drills:
        # Build a small DataFrame for clean display
        df = pd.DataFrame(drills)
        # Order columns
        df_display = df[["from_message_index", "drill", "sets", "reps", "time", "source"]].copy()
        df_display = df_display.rename(columns={
            "from_message_index": "Tip # (message idx)",
            "drill": "Drill",
            "sets": "Sets",
            "reps": "Reps",
            "time": "Time",
            "source": "Snippet"
        })
        # Display table in sidebar
        st.sidebar.dataframe(df_display.reset_index(drop=True), height=400)
        # Also show a short bullet summary for quick glance
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Quick view:**")
        for i, row in df_display.iterrows():
            parts = []
            if row["Sets"]: parts.append(f"{row['Sets']} sets")
            if row["Reps"]: parts.append(f"{row['Reps']} reps")
            if row["Time"]: parts.append(f"{row['Time']}")
            meta = ", ".join(parts) if parts else ""
            st.sidebar.write(f"- **{row['Drill']}** {('— ' + meta) if meta else ''}")
    else:
        st.sidebar.info("No parsed drill summary yet — ask MikeBot for training tips (e.g., 'Give me a dribbling routine').")

    # Main chat area: show full conversation (full MikeBot replies preserved)
    for message in st.session_state.messages:
        avatar_icon = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar_icon):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("What's on your mind? (ask MikeBot for a drill or workout)"):
        # Save + show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(prompt)

        # Show spinner while producing response
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            with st.spinner("MikeBot is drawing up a plan..."):
                response_text = get_gemini_response(prompt)
                # Save assistant message
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.write(response_text)

        # (Sidebar will refresh on next run automatically because session_state.messages changed)


if __name__ == "__main__":
    main()