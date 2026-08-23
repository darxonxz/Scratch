import streamlit as st
import pdfplumber
import re
import uuid

# --- PAGE SETUP ---
st.set_page_config(page_title="Magic To-Do", page_icon="🪄", layout="centered")

# --- MEMORY (SESSION STATE) ---
# This keeps tasks alive so they don't disappear when we click things
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- BRAINS: PARSING LOGIC ---
def extract_tasks(text):
    lines = text.split('\n')
    current_category = "General"
    new_tasks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if it's a task bullet
        is_bullet = re.match(r'^[-*•]\s', line)
        is_keyword = line.lower().startswith(('to do', 'task', 'action'))
        
        if is_bullet or is_keyword:
            clean_task = re.sub(r'^[-*•]\s*(task:|to do:)?\s*', '', line, flags=re.IGNORECASE)
            new_tasks.append({
                "id": str(uuid.uuid4()), # Unique ID for tracking
                "text": clean_task.strip(),
                "category": current_category,
                "completed": False
            })
        else:
            # If it's short and not a task, assume it's a category/heading!
            if len(line) > 2 and len(line) < 40:
                current_category = line.strip().strip(':')
                
    # Add new tasks to our memory
    st.session_state.tasks.extend(new_tasks)

# Callback to handle the checkbox flip
def toggle_task(task_id):
    for t in st.session_state.tasks:
        if t['id'] == task_id:
            # Flip the status to match the checkbox
            t['completed'] = st.session_state[task_id]
            # Throw some confetti if it's checked
            if t['completed']:
                st.toast("Nailed it! 🔨")
            break

# --- UI VISUALS ---
st.title("🪄 Magic To-Do List")

# 1. INPUT AREA (TABS)
tab1, tab2 = st.tabs(["📋 Paste Text", "📄 Upload PDF"])

with tab1:
    pasted_text = st.text_area("Dump your notes, lists, or brain-dump here:")
    if st.button("Extract Tasks from Text 🚀"):
        if pasted_text:
            extract_tasks(pasted_text)
            st.success("Tasks extracted!")
        else:
            st.warning("Paste something first.")

with tab2:
    uploaded_file = st.file_uploader("Drop your PDF here 📥", type="pdf")
    if st.button("Extract Tasks from PDF 🚀"):
        if uploaded_file:
            full_text = ""
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted: full_text += extracted + "\n"
            extract_tasks(full_text)
            st.success("Tasks extracted!")
        else:
            st.warning("Upload a file first.")

st.divider()

# 2. FILTERING AREA
if st.session_state.tasks:
    # Get unique categories
    all_categories = list(set([t['category'] for t in st.session_state.tasks]))
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Slicers/Filters!
        selected_cats = st.multiselect("📂 Filter by Category", all_categories, default=all_categories)
    with col2:
        # Nuke button
        if st.button("🗑️ Clear All"):
            st.session_state.tasks = []
            st.rerun()

    # Apply the filter
    filtered_tasks = [t for t in st.session_state.tasks if t['category'] in selected_cats]
    
    # Split into Active and Done to push checked items to the bottom
    active_tasks = [t for t in filtered_tasks if not t['completed']]
    done_tasks = [t for t in filtered_tasks if t['completed']]

    # 3. RENDER ACTIVE TASKS
    st.subheader(f"🎯 To Do ({len(active_tasks)})")
    for t in active_tasks:
        # We show the category in a little bubble using markdown
        label = f"**{t['text']}**  *(📁 {t['category']})*"
        st.checkbox(label, value=False, key=t['id'], on_change=toggle_task, args=(t['id'],))

    # 4. RENDER DONE TASKS (Moves to bottom & strikes out!)
    if done_tasks:
        st.markdown("---")
        st.subheader(f"✅ Done ({len(done_tasks)})")
        for t in done_tasks:
            # Markdown ~~ adds the strike-through effect
            label = f"~~{t['text']}~~ *(📁 {t['category']})*"
            st.checkbox(label, value=True, key=t['id'], on_change=toggle_task, args=(t['id'],))
else:
    st.info("No tasks yet. Upload a PDF or paste some text above!")