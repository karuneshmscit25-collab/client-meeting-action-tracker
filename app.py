import streamlit as st
import pandas as pd
import re, json
from datetime import datetime

st.set_page_config(page_title="Pulse | Meeting Ops", page_icon="◉", layout="wide")
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Manrope,sans-serif}.stApp{background:#f4f7fa;color:#172733}
[data-testid="stSidebar"]{background:#172733}[data-testid="stSidebar"] *{color:#f4f7fa!important}
.hero{background:linear-gradient(120deg,#173b4b,#176d70,#259a92);color:white;border-radius:22px;padding:27px 30px;margin-bottom:18px;box-shadow:0 12px 28px #173b4b18}
.hero .eyebrow{font:500 11px 'DM Mono',monospace;letter-spacing:2px;opacity:.8}.hero h1{font-size:32px;margin:9px 0 7px;color:white}.hero p{margin:0;color:#e1f4f1;font-size:14px}
.metric{background:white;border:1px solid #e1e8ef;border-radius:16px;padding:16px 18px;min-height:100px}.metric .label{font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:1px;font-weight:800}.metric .num{font-size:28px;font-weight:800;margin-top:5px}
.panel{background:white;border:1px solid #e1e8ef;border-radius:17px;padding:19px 22px;margin:8px 0 16px}.panel h3{margin:0 0 6px;font-size:17px}.muted{color:#718096;font-size:12px}
div.stButton>button{border-radius:10px;font-weight:700;padding:.58rem 1rem}div.stButton>button[kind="primary"]{background:#0f8b8d;color:white}
</style>''', unsafe_allow_html=True)

def fresh():
    return {"title":"Weekly project sync","date":datetime.now().date().isoformat(),"attendees":"","notes":"","decisions":[],"tasks":[],"risks":[],"questions":[],"summary":"","generated":False}
if "data" not in st.session_state: st.session_state.data=fresh()
if "page" not in st.session_state: st.session_state.page="Meeting intake"
d=st.session_state.data

def hero(kicker,title,desc):
    st.markdown(f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{desc}</p></div>',unsafe_allow_html=True)
def metric(label,value,note):
    st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="num">{value}</div><div class="muted">{note}</div></div>',unsafe_allow_html=True)
def split_lines(text):
    result=[]
    for raw in text.splitlines():
        line=re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*','',raw).strip()
        if line:
            result.extend([x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9“])',line) if x.strip()])
    return result
ACTION=r'\b(send|share|create|build|prepare|review|update|fix|test|confirm|schedule|deliver|draft|design|implement|check|provide|complete|finalize|upload|deploy|contact|email|publish|investigate|analyse|analyze|validate|document|approve|collect|follow up|migrate|present|add|remove|write|discuss)\b'
RISK_WORDS=['risk','blocked','blocker','delay','delayed','dependency','depend on','might','may not','concern','issue','uncertain','fail','failure','budget','unavailable','waiting on']
QUESTION_WORDS=['need to clarify','unclear','confirm whether','not sure','unknown','tbd','to be decided','who will','when will']
def owner_of(s):
    m=re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|to)\s+',s)
    if m:return m.group(1)
    m=re.search(r'\b(?:owner|assigned to|responsible person)\s*[:=-]\s*([A-Z][\w.-]+(?:\s+[A-Z][\w.-]+)?)',s,re.I)
    return m.group(1) if m else 'Not stated'
def due_of(s):
    m=re.search(r'\b(20\d{2}-\d{2}-\d{2})\b',s)
    if m:return m.group(1)
    if re.search(r'\btomorrow|today|next week|next month\b',s,re.I): return 'Needs confirmation: relative date'
    m=re.search(r'\b(?:by|due|before|on)\s+((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,?\s+20\d{2})?)',s,re.I)
    return m.group(1)+' (confirm)' if m else 'Not stated'
def extract(text):
    decisions=[];tasks=[];risks=[];questions=[]
    for s in split_lines(text):
        low=s.lower()
        if re.search(r'\b(decided|decision|agreed that|approved|we will use|go with|chosen|confirmed that)\b',low):
            decisions.append({'Decision':s,'Context / rationale':'Not stated in notes','Confirmation':'Review'})
        if any(w in low for w in RISK_WORDS): risks.append({'Risk / dependency':s,'Impact':'Needs assessment','Mitigation / next step':'Not stated','Status':'Open'})
        if '?' in s or any(w in low for w in QUESTION_WORDS): questions.append({'Question':s,'Suggested owner':'Not stated','Status':'Open'})
        if re.search(ACTION,s,re.I):
            task=re.sub(r'^(?:we agreed to|action item:|todo:|to-do:|next step:|action:)\s*','',s,flags=re.I).strip(' .;')
            tasks.append({'Task':task,'Owner':owner_of(s),'Due date':due_of(s),'Priority':'Medium','Status':'Not started','Source note':s})
    def unique(items,key):
        seen=set();out=[]
        for x in items:
            sig=x[key].lower()
            if sig not in seen:seen.add(sig);out.append(x)
        return out
    tasks=unique(tasks,'Task');decisions=unique(decisions,'Decision');risks=unique(risks,'Risk / dependency');questions=unique(questions,'Question')
    return {'tasks':tasks,'decisions':decisions,'risks':risks,'questions':questions,'summary':f'Reviewed {len(split_lines(text))} note line(s). Suggested {len(tasks)} task(s), {len(decisions)} decision(s), {len(risks)} risk/dependency item(s), and {len(questions)} question(s). Review every item before sharing.'}
def df_for(items,cols):return pd.DataFrame(items).reindex(columns=cols).fillna('') if items else pd.DataFrame(columns=cols)
def report(d):
    out=[f"# Meeting Action Brief: {d['title']}",f"**Date:** {d['date']}  \\n**Attendees:** {d['attendees'] or 'Not provided'}",'', '## Summary',d['summary'] or 'Not generated','']
    for title,key,cols in [('Decisions','decisions',['Decision','Context / rationale','Confirmation']),('Action items','tasks',['Task','Owner','Due date','Priority','Status']),('Risks & dependencies','risks',['Risk / dependency','Impact','Mitigation / next step','Status']),('Open questions','questions',['Question','Suggested owner','Status'])]:
        out.append('## '+title)
        if not d[key]:out.append('- None captured.')
        for i,row in enumerate(d[key],1):out.append(f"{i}. "+' | '.join(f"**{c}:** {row.get(c,'') or 'Not stated'}" for c in cols))
        out.append('')
    out += ['## Review reminders','- “Not stated” means the notes did not specify this; no owner or deadline has been guessed.','- Resolve relative dates and verify decisions, risks, and tasks before distributing.']
    return '\n'.join(out)

with st.sidebar:
    st.markdown('<div style="padding:10px 5px 18px"><div style="font:500 11px DM Mono;letter-spacing:2px;color:#8dd9d0">PULSE / WORKSPACE</div><div style="font-size:25px;font-weight:800;margin-top:8px">Meeting Ops</div><div style="font-size:12px;color:#b5c6ce">Turn talk into accountable work.</div></div>',unsafe_allow_html=True)
    st.markdown('---')
    pages=['Meeting intake','Action board','Decisions & risks','Export centre']
    st.session_state.page=st.radio('WORKSPACE',pages,index=pages.index(st.session_state.page),label_visibility='collapsed')
    st.markdown('---');st.markdown('**CURRENT MEETING**');st.caption(d['title'] or 'Untitled meeting');st.caption('🗓 '+(d['date'] or 'Date not set'))
    if st.button('＋  Start fresh meeting',use_container_width=True):
        st.session_state.data=fresh();st.rerun()
    st.markdown('<div style="position:fixed;bottom:20px;font-size:10px;color:#8da3ad">PULSE v1.0 · HUMAN REVIEW REQUIRED</div>',unsafe_allow_html=True)

if st.session_state.page=='Meeting intake':
    hero('01 / CAPTURE','Meeting, made actionable.','Paste raw notes. Pulse separates decisions, commitments, risks, and unknowns—without making up missing details.')
    left,right=st.columns([1,1.7],gap='large')
    with left:
        st.markdown('<div class="panel"><h3>Meeting details</h3><div class="muted">Give this conversation a home.</div></div>',unsafe_allow_html=True)
        title=st.text_input('Meeting title',value=d['title'],key='meeting_title_input')
        date=st.date_input('Meeting date',value=datetime.fromisoformat(d['date']).date(),key='meeting_date_input')
        attendees=st.text_input('Attendees (optional)',value=d['attendees'],placeholder='e.g. Maya, Alex, Priya',key='attendees_input')
    with right:
        st.markdown('<div class="panel"><h3>Raw meeting notes / transcript</h3><div class="muted">Bullets, transcript excerpts, and rough notes are fine.</div></div>',unsafe_allow_html=True)
        sample='''- We agreed to launch the pilot with the existing onboarding flow.\n- Maya will prepare the customer email by 2026-11-03.\n- Alex to review the dashboard copy next week.\n- The data export is blocked because the vendor API is unstable.\n- Need to confirm who owns analytics tracking?\n- Finance may not approve the extra tooling budget.\n- Priya will share the revised wireframes.\n- Should we move the beta review to Friday?'''
        notes=st.text_area('Notes',value=d['notes'],height=290,placeholder='Paste meeting notes here…',label_visibility='collapsed',key='notes_input')
        c1,c2=st.columns(2)
        with c1:
            if st.button('Load sample meeting',use_container_width=True):
                d.update({'title':'Product launch planning','attendees':'Maya, Alex, Priya','notes':sample});st.rerun()
        with c2: run=st.button('✦  Extract action brief',type='primary',use_container_width=True)
    if run:
        d.update({'title':title.strip() or 'Untitled meeting','date':date.isoformat(),'attendees':attendees.strip(),'notes':notes})
        if not notes.strip():st.warning('Add notes first, or load the sample meeting.')
        else:d.update(extract(notes));d['generated']=True;st.session_state.page='Action board';st.rerun()
    st.markdown('<div class="panel"><h3>Designed for trustworthy handoffs</h3><div class="muted">01 — Capture exact notes · 02 — Review editable suggestions · 03 — Confirm what is missing · 04 — Export to your tracker</div></div>',unsafe_allow_html=True)

elif st.session_state.page=='Action board':
    hero('02 / EXECUTION','The action board.','Every extracted item stays editable. Unknown owners and dates remain explicitly marked—not silently filled in.')
    if not d['generated']:st.info('Open Meeting intake, add notes, and select Extract action brief.')
    else:
        tasks=df_for(d['tasks'],['Task','Owner','Due date','Priority','Status','Source note'])
        a,b,c,e=st.columns(4)
        with a:metric('Action items',len(tasks),'captured from notes')
        with b:metric('Unassigned',int((tasks['Owner']=='Not stated').sum()) if len(tasks) else 0,'owner needs confirmation')
        with c:metric('No due date',int(tasks['Due date'].isin(['Not stated','Needs confirmation: relative date']).sum()) if len(tasks) else 0,'deadline needs confirmation')
        with e:metric('Open tasks',int((tasks['Status']!='Done').sum()) if len(tasks) else 0,'not marked complete')
        st.markdown('#### Action items');st.caption('Edit cells directly. Keep “Not stated” until the meeting owner confirms missing details.')
        edited=st.data_editor(tasks,use_container_width=True,num_rows='dynamic',hide_index=True,key='task_editor',column_config={'Priority':st.column_config.SelectboxColumn(options=['Low','Medium','High','Critical']),'Status':st.column_config.SelectboxColumn(options=['Not started','In progress','Blocked','Done'])})
        d['tasks']=edited.fillna('').to_dict('records')
        st.info('Source note is included to help trace each suggested task back to the meeting wording.')

elif st.session_state.page=='Decisions & risks':
    hero('03 / ALIGNMENT','Decisions, risks & unknowns.','Keep the why, the concern, and the unanswered question visible alongside the work.')
    if not d['generated']:st.info('Extract a brief first from Meeting intake.')
    else:
        st.markdown('#### Decisions');st.caption('Confirm that each decision was actually made.')
        x=st.data_editor(df_for(d['decisions'],['Decision','Context / rationale','Confirmation']),use_container_width=True,num_rows='dynamic',hide_index=True,key='decision_editor');d['decisions']=x.fillna('').to_dict('records')
        st.markdown('#### Risks & dependencies')
        x=st.data_editor(df_for(d['risks'],['Risk / dependency','Impact','Mitigation / next step','Status']),use_container_width=True,num_rows='dynamic',hide_index=True,key='risk_editor');d['risks']=x.fillna('').to_dict('records')
        st.markdown('#### Open questions')
        x=st.data_editor(df_for(d['questions'],['Question','Suggested owner','Status']),use_container_width=True,num_rows='dynamic',hide_index=True,key='question_editor');d['questions']=x.fillna('').to_dict('records')
        d['summary']=st.text_area('Meeting summary / interpretation',value=d['summary'],height=90,key='summary_editor')

else:
    hero('04 / HANDOFF','Make the next step portable.','Download a meeting brief or tracker-ready files. Review content before sharing it outside your team.')
    if not d['generated']:st.info('Extract a brief first from Meeting intake.')
    else:
        full=report(d);tasks=df_for(d['tasks'],['Task','Owner','Due date','Priority','Status','Source note']).drop(columns=['Source note'],errors='ignore')
        tasks.insert(0,'Meeting',d['title']);tasks.insert(1,'Meeting date',d['date'])
        left,right=st.columns(2,gap='large')
        with left:
            st.markdown('<div class="panel"><h3>Meeting brief</h3><div class="muted">Decisions, actions, risks, and open questions in one report.</div></div>',unsafe_allow_html=True)
            st.download_button('↓  Download full brief (.md)',full,'meeting_action_brief.md','text/markdown',type='primary',use_container_width=True)
            st.download_button('↓  Download brief (.txt)',full,'meeting_action_brief.txt','text/plain',use_container_width=True)
        with right:
            st.markdown('<div class="panel"><h3>Tracker exports</h3><div class="muted">CSV for Excel / Google Sheets, plus JSON for structured data transfer.</div></div>',unsafe_allow_html=True)
            st.download_button('↓  Export tasks (.csv)',tasks.to_csv(index=False).encode('utf-8-sig'),'meeting_tasks.csv','text/csv',use_container_width=True)
            bundle={'meeting':{'title':d['title'],'date':d['date'],'attendees':d['attendees']},'summary':d['summary'],'decisions':d['decisions'],'tasks':d['tasks'],'risks':d['risks'],'questions':d['questions'],'source_notes':d['notes']}
            st.download_button('↓  Export full data (.json)',json.dumps(bundle,indent=2,ensure_ascii=False),'meeting_action_data.json','application/json',use_container_width=True)
        st.markdown('#### Preview of full brief');st.markdown(full)
        st.markdown('<div class="panel"><h3>Before you share</h3><div class="muted">Confirm unassigned owners · Resolve relative dates · Verify decisions · Review risks · Check confidential content</div></div>',unsafe_allow_html=True)

st.markdown('<div style="padding:24px 0 8px;color:#8996a6;font-size:11px;text-align:center">PULSE MEETING OPS · DRAFT ASSISTANCE, HUMAN CONFIRMATION REQUIRED</div>',unsafe_allow_html=True)
