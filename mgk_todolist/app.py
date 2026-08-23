import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time
import io

# --- 1. PAGE CONFIG & MODERN DARK THEME ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* Global modern UI styling */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4facfe, #00f2fe); }
    
    /* Modern card containers */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background-color: #161B22;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #30363D;
    }
    
    /* Priority Pill Badges */
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CACHED HEAVY UTILITIES (CLOUD OPTIMIZATION) ---
@st.cache_data(show_spinner=False)
def extract_text_from_pdf_bytes(file_bytes):
    """Cached PDF text extractor to prevent re-parsing on UI interactions."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def parse_text_to_tasks(text):
    """Regex parser to detect bullets, numbers, headers, and priority keywords."""
    lines = text.split('\n')
    current_cat = "Imported"
    new_tasks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match bullets (-, *, •), numbers (1., 2.), or task action keywords
        is_bullet = re.match(r'^(?:[-*•]|\d+[\.\)])\s', line)
        is_keyword = re.match(r'^(?:task|to do|todo|action|item)[\s:]', line, re.IGNORECASE)
        
        if is_bullet or is_keyword:
            clean_text = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', line)
            clean_text = re.sub(r'^(?:task|to do|todo|action|item)[\s:]*', '', clean_text, flags=re.IGNORECASE).strip()
            
            if not clean_text:
                continue
                
            # Smart Priority Detection
            low_text = clean_text.lower()
            if any(w in low_text for w in ['urgent', 'asap', 'today', 'critical', 'high', 'p1']):
                prio = "P1 (High)"
            elif any(w in low_text for w in ['medium', 'important', 'soon', 'p2']):
                prio = "P2 (Medium)"
            else:
                prio = "P3 (Low)"
                
            new_tasks.append({
                "id": str(uuid.uuid4()),
                "text": clean_text,
                "category": current_cat,
                "priority": prio,
                "completed": False,
                "subtasks": []
            })
        elif 2 < len(line) < 40 and not line.endswith('.'):
            # Treat short standalone titles as categories
            current_cat = line.strip().strip(':')
                
    st.session_state.tasks.extend(new_tasks)

# --- 3. SESSION STATE INITIALIZATION & SANITIZATION ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# Schema Healing: Ensure every task object maintains valid key structures
for task in st.session_state.tasks:
    task.setdefault('id', str(uuid.uuid4()))
    task.setdefault('text', 'Untitled Task')
    task.setdefault('category', 'General')
    task.setdefault('priority', 'P3 (Low)')
    task.setdefault('completed', False)
    task.setdefault('subtasks', [])

# --- 4. SIDEBAR: FOCUS TIMER & BACKUPS ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    st.caption("TickTick-style Pomodoro Timer")
    timer_mins = st.number_input("Focus duration (mins)", min_value=1, max_value=60, value=25)
    
    if st.button("▶️ Start Focus Timer", type="primary"):
        st.info("Focus session active! Stay on task...")
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Session complete! Great focus session. 🎉")
        st.balloons()
        
    st.divider()
    st.header("💾 Backup & Export")
    if st.session_state.tasks:
        df_export = pd.DataFrame(st.session_state.tasks)
        # Drop complex nested list column for CSV compatibility
        if 'subtasks' in df_export.columns:
            df_export = df_export.drop(columns=['subtasks'])
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Tasks (CSV)", data=csv_data, file_name="my_tasks.csv", mime="text/csv")

# --- 5. DASHBOARD HEADER & PROGRESS METRICS ---
st.title("⚡ TaskFlow Pro")

if st.session_state.tasks:
    total_count = len(st.session_state.tasks)
    done_count = sum(1 for t in st.session_state.tasks if t.get('completed', False))
    progress_val = done_count / total_count if total_count > 0 else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tasks", total_count)
    m2.metric("Completed Tasks", done_count)
    m3.metric("Completion Rate", f"{int(progress_val * 100)}%")
    
    st.progress(progress_val)
    if progress_val == 1.0:
        st.snow()

st.divider()

# --- 6. TASK INPUT HUB (MANUAL, PDF, PASTE) ---
with st.expander("➕ Import / Add Tasks", expanded=not bool(st.session_state.tasks)):
    input_tab1, input_tab2, input_tab3 = st.tabs(["Quick Add", "📄 Upload PDF", "📋 Paste Notes"])
    
    with input_tab1:
        col_qa1, col_qa2, col_qa3 = st.columns([3, 2, 2])
        with col_qa1:
            q_title = st.text_input("Title", placeholder="Task name", label_visibility="collapsed")
        with col_qa2:
            q_cat = st.text_input("Category", placeholder="Category / Folder", label_visibility="collapsed")
        with col_qa3:
            q_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=2, label_visibility="collapsed")
        
        q_subs = st.text_input("Subtasks (comma-separated)", placeholder="Subtask 1, Subtask 2")
        
        if st.button("Add Task 🚀") and q_title:
            sub_list = [{"text": s.strip(), "completed": False} for s in q_subs.split(',') if s.strip()]
            st.session_state.tasks.append({
                "id": str(uuid.uuid4()),
                "text": q_title,
                "category": q_cat if q_cat else "General",
                "priority": q_prio,
                "completed": False,
                "subtasks": sub_list
            })
            st.toast("Task added successfully! 🎯")
            st.rerun()

    with input_tab2:
        uploaded_pdf = st.file_uploader("Drop your PDF here 📥", type="pdf")
        if st.button("Extract PDF Tasks 🚀") and uploaded_pdf:
            pdf_bytes = uploaded_pdf.read()
            pdf_text = extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                parse_text_to_tasks(pdf_text)
                st.toast("PDF Tasks Extracted! 🎉")
                st.rerun()
            else:
                st.warning("Could not read text from this PDF.")

    with input_tab3:
        pasted_text = st.text_area("Paste text or bullet points here:")
        if st.button("Extract Pasted Tasks 🚀") and pasted_text:
            parse_text_to_tasks(pasted_text)
            st.toast("Notes Extracted! 🎉")
            st.rerun()

# --- 7. WORKSPACE MODES (FOCUS CHECKLIST VS BULK ORGANIZER) ---
if st.session_state.tasks:
    checklist_mode, organizer_mode = st.tabs(["🎯 Focus Checklist Mode", "🛠️ Bulk Organizer Mode"])

    # ==========================================
    # MODE 1: FOCUS CHECKLIST (DOPAMINE DRIVEN)
    # ==========================================
    with checklist_mode:
        f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 2, 1])
        with f_col1:
            search_str = st.text_input("🔍 Search", placeholder="Filter by keyword...").lower()
        with f_col2:
            cats_available = list(set(t.get('category', 'General') for t in st.session_state.tasks))
            sel_cats = st.multiselect("Category Slicer", cats_available, default=cats_available)
        with f_col3:
            sel_prios = st.multiselect("Priority Slicer", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"])
        with f_col4:
            st.write("")
            st.write("")
            if st.button("🗑️ Clear All"):
                st.session_state.tasks = []
                st.rerun()

        # Apply Filters Safely
        filtered_tasks = [
            t for t in st.session_state.tasks
            if (search_str in t.get('text', '').lower() or search_str in t.get('category', '').lower())
            and t.get('category', 'General') in sel_cats
            and t.get('priority', 'P3 (Low)') in sel_prios
        ]
        
        active_items = [t for t in filtered_tasks if not t.get('completed', False)]
        done_items = [t for t in filtered_tasks if t.get('completed', False)]

        # --- Active Tasks Section ---
        st.subheader(f"🎯 To-Do ({len(active_items)})")
        for t in active_items:
            prio = t.get('priority', 'P3 (Low)')
            p_class = "badge-p1" if "P1" in prio else ("badge-p2" if "P2" in prio else "badge-p3")
            
            c_chk, c_text, c_edit = st.columns([0.05, 0.85, 0.1])
            with c_chk:
                if st.checkbox("", value=False, key=f"chk_{t['id']}"):
                    t['completed'] = True
                    st.toast("Nailed it! Task moved to Done. 🔨")
                    st.rerun()
            with c_text:
                st.markdown(
                    f"**{t.get('text', '')}** <span class='{p_class}'>{prio}</span> <span class='cat-badge'>📁 {t.get('category', 'General')}</span>",
                    unsafe_allow_html=True
                )
                # Subtasks Rendering
                if t.get('subtasks'):
                    sub_done = sum(1 for s in t['subtasks'] if s.get('completed', False))
                    with st.expander(f"Subtasks ({sub_done}/{len(t['subtasks'])})"):
                        for idx, sub in enumerate(t['subtasks']):
                            sub_chk = st.checkbox(sub['text'], value=sub.get('completed', False), key=f"sub_{t['id']}_{idx}")
                            sub['completed'] = sub_chk

            with c_edit:
                # Inline Popover Edit
                with st.popover("✏️"):
                    st.caption("Quick Edit")
                    edit_txt = st.text_input("Task Title", t.get('text', ''), key=f"et_{t['id']}")
                    edit_cat = st.text_input("Category", t.get('category', ''), key=f"ec_{t['id']}")
                    prio_options = ["P1 (High)", "P2 (Medium)", "P3 (Low)"]
                    current_prio_idx = prio_options.index(prio) if prio in prio_options else 2
                    edit_prio = st.selectbox("Priority", prio_options, index=current_prio_idx, key=f"ep_{t['id']}")
                    
                    if st.button("Save", key=f"eb_{t['id']}"):
                        t['text'] = edit_txt
                        t['category'] = edit_cat
                        t['priority'] = edit_prio
                        st.rerun()

        # --- Done Tasks Section (Auto-Pushed to Bottom) ---
        if done_items:
            st.markdown("---")
            st.subheader(f"✅ Completed ({len(done_items)})")
            for t in done_items:
                c_chk, c_text = st.columns([0.05, 0.95])
                with c_chk:
                    if not st.checkbox("", value=True, key=f"chk_done_{t['id']}"):
                        t['completed'] = False
                        st.rerun()
                with c_text:
                    st.markdown(
                        f"~~{t.get('text', '')}~~ <span class='cat-badge'>📁 {t.get('category', 'General')}</span>",
                        unsafe_allow_html=True
                    )

    # ==========================================
    # MODE 2: BULK ORGANIZER (SPREADSHEET SPREE)
    # ==========================================
    with organizer_mode:
        st.info("💡 **Bulk Edit Mode:** Edit categories, titles, or priorities across all rows at once. You can add or delete rows dynamically.")
        
        df_editor = pd.DataFrame(st.session_state.tasks)
        
        # Interactive Grid
        edited_grid = st.data_editor(
            df_editor,
            column_config={
                "id": None,          # Hide raw UUIDs
                "subtasks": None,    # Hide nested structures
                "completed": st.column_config.CheckboxColumn("Done?", width="small"),
                "text": st.column_config.TextColumn("Task Title", width="large", required=True),
                "category": st.column_config.TextColumn("Category", width="medium"),
                "priority": st.column_config.SelectboxColumn("Priority", options=["P1 (High)", "P2 (Medium)", "P3 (Low)"], width="medium")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="spreadsheet_editor"
        )
        
        if st.button("💾 Apply Bulk Changes", type="primary"):
            updated_task_list = []
            for _, row in edited_grid.iterrows():
                # Skip empty task entries
                if pd.isna(row.get('text')) or str(row.get('text')).strip() == "":
                    continue
                    
                row_id = row.get('id') if pd.notna(row.get('id')) and row.get('id') else str(uuid.uuid4())
                subs = row.get('subtasks') if isinstance(row.get('subtasks'), list) else []

                updated_task_list.append({
                    "id": str(row_id),
                    "text": str(row['text']).strip(),
                    "category": str(row['category']).strip() if pd.notna(row['category']) else "General",
                    "priority": str(row['priority']) if pd.notna(row['priority']) else "P3 (Low)",
                    "completed": bool(row.get('completed', False)),
                    "subtasks": subs
                })
            
            st.session_state.tasks = updated_task_list
            st.success("Changes saved successfully! 🎉")
            time.sleep(0.4)
            st.rerun()
