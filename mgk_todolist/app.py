import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. STATE INITIALIZATION ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'feedback_msg' not in st.session_state:
    st.session_state.feedback_msg = None

if 'q_title' not in st.session_state: st.session_state.q_title = ""
if 'q_cat' not in st.session_state: st.session_state.q_cat = ""
if 'q_subs' not in st.session_state: st.session_state.q_subs = ""
if 'paste_area' not in st.session_state: st.session_state.paste_area = ""

# --- 3. EXTRACTION ENGINE (WITH SMART FALLBACK) ---
def extract_tasks_from_text(raw_text, source_name="Imported"):
    if not raw_text or not raw_text.strip():
        st.session_state.feedback_msg = ("warning", "No readable text found!")
        return

    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    new_tasks = []
    current_cat = source_name

    # Step A: Attempt Strict Parsing (Bullets, Numbers, Keywords)
    for line in lines:
        is_bullet = re.match(r'^(?:[-*•▪►]|\d+[\.\)]|\(?\d+\))\s', line)
        is_keyword = re.match(r'^(?:task|to do|todo|action|item|q\d+|question)[\s:]', line, re.IGNORECASE)

        if is_bullet or is_keyword:
            clean = re.sub(r'^(?:[-*•▪►]|\d+[\.\)]|\(?\d+\))\s*', '', line)
            clean = re.sub(r'^(?:task|to do|todo|action|item|q\d+|question)[\s:]*', '', clean, flags=re.IGNORECASE).strip()

            if clean:
                low = clean.lower()
                prio = "P1 (High)" if any(w in low for w in ['urgent', 'asap', 'critical']) else ("P2 (Medium)" if any(w in low for w in ['medium', 'important']) else "P3 (Low)")
                new_tasks.append({
                    "id": str(uuid.uuid4()),
                    "text": clean,
                    "category": current_cat,
                    "priority": prio,
                    "completed": False,
                    "subtasks": []
                })
        elif 2 < len(line) < 35 and not line.endswith('.'):
            current_cat = line.strip().strip(':')

    # Step B: Smart Fallback (If 0 strict tasks were found, treat all non-empty lines as tasks)
    if not new_tasks:
        for line in lines:
            if len(line) > 2:
                low = line.lower()
                prio = "P1 (High)" if any(w in low for w in ['urgent', 'asap', 'critical']) else ("P2 (Medium)" if any(w in low for w in ['medium', 'important']) else "P3 (Low)")
                new_tasks.append({
                    "id": str(uuid.uuid4()),
                    "text": line,
                    "category": source_name,
                    "priority": prio,
                    "completed": False,
                    "subtasks": []
                })

    if new_tasks:
        st.session_state.tasks.extend(new_tasks)
        st.session_state.feedback_msg = ("success", f"Extracted {len(new_tasks)} tasks successfully! 🎉")
    else:
        st.session_state.feedback_msg = ("warning", "Could not extract tasks from document.")

# --- 4. CALLBACK FUNCTIONS ---
def add_quick_task():
    title = st.session_state.q_title
    if title.strip():
        cat = st.session_state.q_cat.strip() if st.session_state.q_cat.strip() else "General"
        subs = [{"text": s.strip(), "completed": False} for s in st.session_state.q_subs.split(',') if s.strip()]
        
        st.session_state.tasks.append({
            "id": str(uuid.uuid4()),
            "text": title.strip(),
            "category": cat,
            "priority": st.session_state.q_prio,
            "completed": False,
            "subtasks": subs
        })
        st.session_state.q_title = ""
        st.session_state.q_cat = ""
        st.session_state.q_subs = ""
        st.session_state.feedback_msg = ("success", "Task added! 🎯")

def process_pdf():
    if st.session_state.pdf_uploader is not None:
        try:
            pdf_bytes = st.session_state.pdf_uploader.getvalue()
            text = ""
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            extract_tasks_from_text(text, source_name="PDF Import")
        except Exception as e:
            st.session_state.feedback_msg = ("error", f"PDF Read Error: {e}")
    else:
        st.session_state.feedback_msg = ("warning", "Please upload a PDF file first!")

def process_paste():
    if st.session_state.paste_area:
        extract_tasks_from_text(st.session_state.paste_area, source_name="Pasted Notes")
        st.session_state.paste_area = ""

def clear_all_tasks():
    st.session_state.tasks = []
    st.session_state.feedback_msg = ("info", "All tasks cleared.")

# --- 5. SIDEBAR: TIMER & EXPORT ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    timer_mins = st.number_input("Focus duration (mins)", min_value=1, max_value=60, value=25)
    if st.button("▶️ Start Focus Timer", type="primary"):
        st.info("Focus session active! Stay on task...")
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Session complete! 🎉")
        st.balloons()
        
    st.divider()
    st.header("💾 Export Data")
    if st.session_state.tasks:
        export_df = pd.DataFrame([{
            "Task Title": t.get("text", ""),
            "Category": t.get("category", ""),
            "Priority": t.get("priority", ""),
            "Status": "Done" if t.get("completed") else "Pending"
        } for t in st.session_state.tasks])
        
        st.download_button(
            label="📥 Download CSV",
            data=export_df.to_csv(index=False).encode('utf-8'),
            file_name="taskflow_export.csv",
            mime="text/csv"
        )
    
    st.divider()
    st.button("🗑️ Clear All Tasks", on_click=clear_all_tasks, type="secondary")

# --- 6. HEADER & METRICS ---
st.title("⚡ TaskFlow Pro")

if st.session_state.feedback_msg:
    msg_type, msg_txt = st.session_state.feedback_msg
    if msg_type == "success": st.success(msg_txt)
    elif msg_type == "warning": st.warning(msg_txt)
    elif msg_type == "error": st.error(msg_txt)
    elif msg_type == "info": st.info(msg_txt)
    st.session_state.feedback_msg = None

if st.session_state.tasks:
    total_count = len(st.session_state.tasks)
    done_count = sum(1 for t in st.session_state.tasks if t.get('completed', False))
    progress_val = done_count / total_count if total_count > 0 else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tasks", total_count)
    m2.metric("Completed Tasks", done_count)
    m3.metric("Completion Rate", f"{int(progress_val * 100)}%")
    
    st.progress(progress_val)

st.divider()

# --- 7. INPUT HUB ---
with st.expander("➕ Import / Add Tasks", expanded=not bool(st.session_state.tasks)):
    input_tab1, input_tab2, input_tab3 = st.tabs(["Quick Add", "📄 Upload PDF", "📋 Paste Notes"])
    
    with input_tab1:
        col_qa1, col_qa2, col_qa3 = st.columns([3, 2, 2])
        with col_qa1:
            st.text_input("Task Title", key="q_title", placeholder="Enter task name...")
        with col_qa2:
            st.text_input("Category", key="q_cat", placeholder="Project / Area")
        with col_qa3:
            st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=2, key="q_prio")
        st.text_input("Subtasks (comma-separated)", key="q_subs", placeholder="Subtask 1, Subtask 2")
        st.button("Add Task 🚀", on_click=add_quick_task, type="primary")

    with input_tab2:
        st.file_uploader("Drop your PDF here 📥", type="pdf", key="pdf_uploader")
        st.button("Extract PDF Tasks 🚀", on_click=process_pdf)

    with input_tab3:
        st.text_area("Paste text or bullet points here:", height=150, key="paste_area")
        st.button("Extract Pasted Tasks 🚀", on_click=process_paste)

# --- 8. WORKSPACE MODES ---
if st.session_state.tasks:
    checklist_mode, organizer_mode = st.tabs(["🎯 Focus Checklist Mode", "🛠️ Bulk Organizer Mode"])

    # --- CHECKLIST MODE ---
    with checklist_mode:
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            search_str = st.text_input("🔍 Search", placeholder="Filter by keyword...").lower()
        with c2:
            cats_available = list(set(t.get('category', 'General') for t in st.session_state.tasks))
            sel_cats = st.multiselect("Category Slicer", cats_available, default=cats_available)
        with c3:
            sel_prios = st.multiselect("Priority Slicer", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"])

        filtered_tasks = [
            t for t in st.session_state.tasks
            if (search_str in t.get('text', '').lower() or search_str in t.get('category', '').lower())
            and t.get('category', 'General') in sel_cats
            and t.get('priority', 'P3 (Low)') in sel_prios
        ]
        
        active_items = [t for t in filtered_tasks if not t.get('completed', False)]
        done_items = [t for t in filtered_tasks if t.get('completed', False)]

        st.subheader(f"🎯 To-Do ({len(active_items)})")
        for i, t in enumerate(active_items):
            prio = t.get('priority', 'P3 (Low)')
            p_class = "badge-p1" if "P1" in prio else ("badge-p2" if "P2" in prio else "badge-p3")
            
            c_chk, c_text = st.columns([0.05, 0.95])
            with c_chk:
                if st.checkbox("", value=False, key=f"act_chk_{t['id']}_{i}"):
                    t['completed'] = True
                    st.rerun()
            with c_text:
                st.markdown(
                    f"**{t.get('text', '')}** <span class='{p_class}'>{prio}</span> <span class='cat-badge'>📁 {t.get('category', 'General')}</span>",
                    unsafe_allow_html=True
                )
                if t.get('subtasks'):
                    with st.expander("Subtasks"):
                        for idx, sub in enumerate(t['subtasks']):
                            sub_chk = st.checkbox(sub['text'], value=sub.get('completed', False), key=f"sub_{t['id']}_{idx}")
                            sub['completed'] = sub_chk

        if done_items:
            st.markdown("---")
            st.subheader(f"✅ Completed ({len(done_items)})")
            for i, t in enumerate(done_items):
                c_chk, c_text = st.columns([0.05, 0.95])
                with c_chk:
                    if not st.checkbox("", value=True, key=f"don_chk_{t['id']}_{i}"):
                        t['completed'] = False
                        st.rerun()
                with c_text:
                    st.markdown(f"~~{t.get('text', '')}~~ <span class='cat-badge'>📁 {t.get('category', 'General')}</span>", unsafe_allow_html=True)

    # --- BULK ORGANIZER MODE ---
    with organizer_mode:
        st.info("💡 **Bulk Edit Mode:** Double-click any cell to edit titles, categories, or priorities.")
        
        df_editor = pd.DataFrame(st.session_state.tasks)
        
        edited_grid = st.data_editor(
            df_editor,
            column_config={
                "id": None,
                "subtasks": None,
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
            updated_tasks = []
            for _, row in edited_grid.iterrows():
                if pd.isna(row.get('text')) or str(row.get('text')).strip() == "":
                    continue
                updated_tasks.append({
                    "id": str(row.get('id', uuid.uuid4())),
                    "text": str(row['text']).strip(),
                    "category": str(row['category']).strip() if pd.notna(row['category']) else "General",
                    "priority": str(row['priority']) if pd.notna(row['priority']) else "P3 (Low)",
                    "completed": bool(row.get('completed', False)),
                    "subtasks": row.get('subtasks', [])
                })
            
            st.session_state.tasks = updated_tasks
            st.session_state.feedback_msg = ("success", "Bulk changes saved! 🎉")
            st.rerun()
