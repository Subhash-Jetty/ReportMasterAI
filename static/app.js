/**
 * ReportMaster AI — Main Application
 */
const API_BASE='';let isQuerying=false;let currentMessages=[];let voiceActive=false;let recognition=null;

document.addEventListener('DOMContentLoaded',()=>{
  if(!requireAuth()){return}
  initTheme();initUser();initUpload();initSidebar();initTextarea();initKeyboard();
  loadIndexStatus();loadConversationList();updateUserStatsUI();setGreeting();
});

function setGreeting(){
  const h=new Date().getHours();const g=h<12?'Good morning':h<17?'Good afternoon':'Good evening';
  const session=getSession();const name=session?session.name.split(' ')[0]:'';
  const el=document.getElementById('welcome-greeting');
  if(el)el.textContent=name?`${g}, ${name}`:g;
}

function initUser(){
  const session=getSession();if(!session)return;
  const avatar=document.getElementById('user-avatar');
  const nameEl=document.getElementById('user-display-name');
  const emailEl=document.getElementById('user-display-email');
  if(avatar)avatar.textContent=session.name.charAt(0).toUpperCase();
  if(nameEl)nameEl.textContent=session.name;
  if(emailEl)emailEl.textContent=session.email;
}

function updateUserStatsUI(){
  const s=getUserStats();
  const q=document.getElementById('ustat-queries');
  const a=document.getElementById('ustat-avg');
  const c=document.getElementById('ustat-convs');
  if(q)q.textContent=s.queries;
  if(a)a.textContent=s.avgTime+'s';
  if(c)c.textContent=s.conversations;
}

function initSidebar(){
  const sidebar=document.getElementById('sidebar');
  const overlay=document.getElementById('sidebar-overlay');
  const menuBtn=document.getElementById('mobile-menu-btn');
  if(menuBtn)menuBtn.addEventListener('click',()=>{sidebar.classList.toggle('open');overlay.classList.toggle('open')});
  if(overlay)overlay.addEventListener('click',()=>{sidebar.classList.remove('open');overlay.classList.remove('open')});
}

function initTextarea(){
  const ta=document.getElementById('query-input');
  ta.addEventListener('input',()=>{ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,150)+'px'});
  ta.addEventListener('keydown',(e)=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submitQuery()}});
}

function initKeyboard(){
  document.addEventListener('keydown',(e)=>{
    if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();openCommandPalette()}
    if(e.key==='Escape'){closeCommandPalette()}
    if(e.key==='/'&&!e.ctrlKey&&document.activeElement.tagName!=='INPUT'&&document.activeElement.tagName!=='TEXTAREA'){
      e.preventDefault();document.getElementById('query-input').focus()}
    if((e.ctrlKey||e.metaKey)&&e.key==='d'){e.preventDefault();handleThemeToggle()}
  });
}

// ============ Index Status ============
async function loadIndexStatus(){
  try{
    const r=await fetch(`${API_BASE}/api/documents`);if(!r.ok)throw new Error('Failed');
    const d=await r.json();updateStats(d);renderDocumentList(d.documents);updateSystemStatus(d.index_ready);
  }catch(e){console.error(e);showToast('Failed to load index','error');updateSystemStatus(false)}
}
function updateStats(d){
  document.getElementById('stat-docs').textContent=d.total_documents;
  document.getElementById('stat-chunks').textContent=d.total_chunks;
  document.getElementById('stat-model').textContent=d.embedding_model.replace('all-','').replace('-v2','');
}
function updateSystemStatus(ready){
  const ind=document.getElementById('status-indicator');const lbl=document.getElementById('status-label');
  if(ready){ind.classList.add('ready');lbl.textContent='Ready'}else{ind.classList.remove('ready');lbl.textContent='No Index'}
}

// ============ Chat ============
async function submitQuery(){
  const input=document.getElementById('query-input');const q=input.value.trim();
  if(!q){showToast('Please type a question','error');input.focus();return}
  if(isQuerying)return;isQuerying=true;
  const welcome=document.getElementById('welcome-screen');if(welcome)welcome.remove();
  addUserMessage(q);currentMessages.push({role:'user',text:q});
  input.value='';input.style.height='auto';
  const btn=document.getElementById('btn-query');btn.disabled=true;
  showTypingIndicator();
  try{
    const r=await fetch(`${API_BASE}/api/query`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
    if(!r.ok){const err=await r.json();throw new Error(typeof err.detail==='string'?err.detail:'Query failed')}
    const d=await r.json();removeTypingIndicator();addAIMessage(d);
    currentMessages.push({role:'ai',text:d.answer,sources:d.sources,time:d.processing_time,model:d.model_used});
    trackQuery(d.processing_time);updateUserStatsUI();autoSaveConversation();
  }catch(e){
    console.error(e);removeTypingIndicator();addErrorMessage(e.message);showToast(e.message,'error');
  }finally{isQuerying=false;btn.disabled=false;input.focus()}
}

function askQuick(el){
  const input=document.getElementById('query-input');
  const ct=el.querySelector('.chip-text');
  input.value=ct?ct.textContent.trim():el.textContent.trim();
  submitQuery();
}

// ============ Messages ============
function addUserMessage(text){
  const c=document.getElementById('chat-messages');const row=document.createElement('div');
  row.className='message-row user';
  row.innerHTML=`<div class="message-bubble">${escapeHtml(text)}</div>`;
  c.appendChild(row);scrollToBottom();
}

function addAIMessage(data){
  const c=document.getElementById('chat-messages');const row=document.createElement('div');
  row.className='message-row ai';
  let src='';
  if(data.sources&&data.sources.length>0){
    const cards=data.sources.map(s=>{
      const sc=s.relevance_score>=.8?'score-high':s.relevance_score>=.6?'score-mid':'score-low';
      return `<div class="source-chip"><div class="source-chip-header"><span class="source-chip-name">${escapeHtml(s.document_name)}</span><span class="source-chip-score ${sc}">${(s.relevance_score*100).toFixed(0)}%</span></div><div class="source-chip-text">${escapeHtml(s.content)}</div></div>`;
    }).join('');
    const tid='src-'+Date.now();
    src=`<div class="sources-accordion"><button class="sources-toggle" onclick="toggleSources('${tid}',this)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>${data.sources.length} source${data.sources.length>1?'s':''} cited</button><div class="sources-list" id="${tid}">${cards}</div></div>`;
  }
  const answerId='ans-'+Date.now();
  row.innerHTML=`<div class="ai-avatar">R</div><div><div class="message-bubble"><div class="ai-answer" id="${answerId}">${formatAnswer(data.answer)}</div>${src}</div><div class="message-meta"><span>⏱ ${data.processing_time.toFixed(2)}s</span><span>${escapeHtml(data.model_used)}</span></div><div class="message-actions"><button class="msg-action" onclick="copyAnswer('${answerId}')" title="Copy"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button><button class="msg-action" onclick="rateMessage(this,'up')" title="Helpful"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg></button><button class="msg-action" onclick="rateMessage(this,'down')" title="Not helpful"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/></svg></button></div></div>`;
  c.appendChild(row);scrollToBottom();
}

function addErrorMessage(text){
  const c=document.getElementById('chat-messages');const row=document.createElement('div');
  row.className='message-row ai';
  row.innerHTML=`<div class="ai-avatar" style="background:linear-gradient(135deg,#C53030,#E53E3E)">!</div><div class="message-bubble" style="border-color:rgba(197,48,48,.2)"><p style="color:var(--danger)">Sorry, something went wrong: ${escapeHtml(text)}</p></div>`;
  c.appendChild(row);scrollToBottom();
}

function showTypingIndicator(){
  const c=document.getElementById('chat-messages');const row=document.createElement('div');
  row.className='typing-row';row.id='typing-indicator';
  row.innerHTML=`<div class="ai-avatar" style="margin-right:.5rem">R</div><div class="typing-indicator"><div class="typing-dots"><span></span><span></span><span></span></div><span class="typing-label">Searching documents...</span></div>`;
  c.appendChild(row);scrollToBottom();
}
function removeTypingIndicator(){const el=document.getElementById('typing-indicator');if(el)el.remove()}

function toggleSources(id,btn){const l=document.getElementById(id);if(l){l.classList.toggle('open');btn.classList.toggle('open')}}
function scrollToBottom(){const c=document.getElementById('chat-messages');requestAnimationFrame(()=>{c.scrollTop=c.scrollHeight})}

// ============ Message Actions ============
function copyAnswer(id){
  const el=document.getElementById(id);if(!el)return;
  navigator.clipboard.writeText(el.innerText).then(()=>showToast('Copied to clipboard','success')).catch(()=>showToast('Failed to copy','error'));
}
function rateMessage(btn,type){
  btn.style.color=type==='up'?'var(--success)':'var(--danger)';
  btn.style.borderColor=type==='up'?'var(--success)':'var(--danger)';
  showToast(type==='up'?'Thanks for the feedback!':'Sorry about that. We\'ll improve.','info');
}

// ============ Answer Format ============
function formatAnswer(text){
  let h=escapeHtml(text);
  h=h.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>');
  h=h.replace(/__(.*?)__/g,'<strong>$1</strong>');
  h=h.replace(/^### (.*$)/gm,'<h3>$1</h3>');
  h=h.replace(/^## (.*$)/gm,'<h2>$1</h2>');
  h=h.replace(/^[-•] (.*$)/gm,'<li>$1</li>');
  h=h.replace(/^(\d+)\. (.*$)/gm,'<li>$1. $2</li>');
  h=h.replace(/((?:<li>.*<\/li>\n?)+)/g,'<ul>$1</ul>');
  h=h.replace(/\[Source:\s*(.*?)\]/g,'<span class="source-cite">[Source: $1]</span>');
  h=h.replace(/\n\n/g,'</p><p>');
  h=h.replace(/\n/g,'<br>');
  return `<p>${h}</p>`;
}

// ============ Documents ============
function renderDocumentList(docs){
  const c=document.getElementById('doc-list');const ld=document.getElementById('doc-loading');if(ld)ld.remove();
  if(!docs||docs.length===0){c.innerHTML=`<div class="doc-list-loading"><span style="opacity:.5">No documents indexed</span></div>`;return}
  c.innerHTML=docs.map(d=>`<div class="doc-item" id="doc-${sanitizeId(d.name)}"><div class="doc-info"><div class="doc-name"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>${escapeHtml(d.name)}</div><div class="doc-meta">${d.chunk_count} chunks · ${formatBytes(d.size_bytes)}</div></div><button class="doc-del-btn" onclick="deleteDocument('${escapeHtml(d.name)}')" title="Remove"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div>`).join('');
}

async function deleteDocument(name){
  if(!confirm(`Remove "${name}"?`))return;
  try{const r=await fetch(`${API_BASE}/api/documents/${encodeURIComponent(name)}`,{method:'DELETE'});if(!r.ok)throw new Error('Failed');showToast(`Removed "${name}"`,'success');loadIndexStatus()}catch(e){showToast(e.message,'error')}
}

async function reindexAll(){
  const btn=document.getElementById('btn-reindex');btn.classList.add('spinning');btn.disabled=true;
  try{const r=await fetch(`${API_BASE}/api/documents/reindex`,{method:'POST'});if(!r.ok)throw new Error('Failed');const d=await r.json();showToast(`Re-indexed ${d.total_documents} docs`,'success');loadIndexStatus()}catch(e){showToast(e.message,'error')}finally{btn.classList.remove('spinning');btn.disabled=false}
}

// ============ Upload ============
function initUpload(){
  const area=document.getElementById('upload-area');const fi=document.getElementById('file-input');
  area.addEventListener('click',()=>fi.click());
  area.addEventListener('dragover',(e)=>{e.preventDefault();area.classList.add('dragover')});
  area.addEventListener('dragleave',()=>area.classList.remove('dragover'));
  area.addEventListener('drop',(e)=>{e.preventDefault();area.classList.remove('dragover');if(e.dataTransfer.files.length>0)uploadFile(e.dataTransfer.files[0])});
  fi.addEventListener('change',(e)=>{if(e.target.files.length>0){uploadFile(e.target.files[0]);e.target.value=''}});
}

async function uploadFile(file){
  if(!file.name.endsWith('.txt')){showToast('Only .txt files supported','error');return}
  if(file.size>10*1024*1024){showToast('File too large (max 10MB)','error');return}
  showToast(`Uploading "${file.name}"...`,'info');
  const fd=new FormData();fd.append('file',file);
  try{const r=await fetch(`${API_BASE}/api/documents/upload`,{method:'POST',body:fd});if(!r.ok){const e=await r.json();throw new Error(e.detail||'Upload failed')}const d=await r.json();showToast(`${d.message} (${d.chunks_created} chunks)`,'success');loadIndexStatus()}catch(e){showToast(e.message,'error')}
}

// ============ Conversations ============
function autoSaveConversation(){
  if(currentMessages.length>0){
    saveConversation(currentMessages);loadConversationList();
  }
}

function loadConversationList(){
  const list=document.getElementById('conv-list');const convs=getConversations();
  if(convs.length===0){list.innerHTML='';return}
  list.innerHTML=convs.slice(0,10).map(c=>`<button class="conv-item" onclick="loadConversation('${c.id}')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span class="conv-preview">${escapeHtml(c.preview)}</span></button>`).join('');
}

function loadConversation(id){
  const conv=getConversation(id);if(!conv)return;
  const c=document.getElementById('chat-messages');c.innerHTML='';
  currentMessages=conv.messages||[];
  currentMessages.forEach(m=>{
    if(m.role==='user')addUserMessage(m.text);
    else if(m.role==='ai')addAIMessage({answer:m.text,sources:m.sources||[],processing_time:m.time||0,model_used:m.model||''});
  });
  const title=document.getElementById('top-bar-title');
  if(title)title.textContent=conv.preview.substring(0,40);
}

function startNewChat(){
  currentMessages=[];
  const c=document.getElementById('chat-messages');
  c.innerHTML=`<div class="welcome-screen" id="welcome-screen"><div class="welcome-icon">R</div><h2 class="welcome-title" id="welcome-greeting">New Conversation</h2><p class="welcome-subtitle">Ask me anything about accounting standards, compliance frameworks, or financial reporting.</p></div>`;
  const title=document.getElementById('top-bar-title');if(title)title.textContent='New Conversation';
  setGreeting();
}

// ============ Voice Input ============
function toggleVoiceInput(){
  if(!('webkitSpeechRecognition' in window)&&!('SpeechRecognition' in window)){showToast('Voice not supported in this browser','error');return}
  const btn=document.getElementById('btn-voice');const btn2=document.getElementById('btn-voice-inline');
  if(voiceActive){
    if(recognition)recognition.stop();voiceActive=false;
    if(btn)btn.classList.remove('active');if(btn2)btn2.classList.remove('recording');
    return;
  }
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang='en-US';
  recognition.onresult=(e)=>{
    const t=e.results[0][0].transcript;document.getElementById('query-input').value=t;
    voiceActive=false;if(btn)btn.classList.remove('active');if(btn2)btn2.classList.remove('recording');
    showToast('Voice captured','success');
  };
  recognition.onerror=()=>{voiceActive=false;if(btn)btn.classList.remove('active');if(btn2)btn2.classList.remove('recording');showToast('Voice error','error')};
  recognition.onend=()=>{voiceActive=false;if(btn)btn.classList.remove('active');if(btn2)btn2.classList.remove('recording')};
  recognition.start();voiceActive=true;
  if(btn)btn.classList.add('active');if(btn2)btn2.classList.add('recording');
  showToast('Listening...','info');
}

// ============ Export ============
function exportChat(){
  if(currentMessages.length===0){showToast('No messages to export','error');return}
  let md='# ReportMaster AI — Chat Export\n\n';
  md+=`Exported: ${new Date().toLocaleString()}\n\n---\n\n`;
  currentMessages.forEach(m=>{
    if(m.role==='user')md+=`**You:** ${m.text}\n\n`;
    else md+=`**ReportMaster AI:** ${m.text}\n\n`;
  });
  const blob=new Blob([md],{type:'text/markdown'});const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=`reportmaster-chat-${Date.now()}.md`;a.click();
  URL.revokeObjectURL(url);showToast('Chat exported','success');
}

// ============ Theme ============
function handleThemeToggle(){
  const next=toggleTheme();
  const btn=document.getElementById('btn-theme');
  if(next==='dark'){btn.innerHTML='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><span class="kbd-hint">⌘+D</span>'}
  else{btn.innerHTML='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg><span class="kbd-hint">⌘+D</span>'}
  showToast(`${next==='dark'?'Dark':'Light'} mode`,'info');
}

// ============ Command Palette ============
const commands=[
  {label:'New Conversation',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',action:()=>{startNewChat();closeCommandPalette()},kbd:''},
  {label:'Toggle Theme',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/></svg>',action:()=>{handleThemeToggle();closeCommandPalette()},kbd:'Ctrl+D'},
  {label:'Export Chat',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',action:()=>{exportChat();closeCommandPalette()},kbd:''},
  {label:'Voice Input',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/></svg>',action:()=>{toggleVoiceInput();closeCommandPalette()},kbd:''},
  {label:'Re-index Documents',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/></svg>',action:()=>{reindexAll();closeCommandPalette()},kbd:''},
  {label:'ASC 606 Revenue Recognition',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>',action:()=>{document.getElementById('query-input').value='What are the five steps of ASC 606?';submitQuery();closeCommandPalette()},kbd:''},
  {label:'ASC 842 Lease Classification',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>',action:()=>{document.getElementById('query-input').value='How are leases classified under ASC 842?';submitQuery();closeCommandPalette()},kbd:''},
  {label:'Sign Out',icon:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/></svg>',action:()=>{logoutUser()},kbd:''},
];

function openCommandPalette(){
  const o=document.getElementById('cmd-overlay');o.classList.add('open');
  const inp=document.getElementById('cmd-input');inp.value='';inp.focus();
  renderCommands(commands);
}
function closeCommandPalette(e){
  if(e&&e.target!==document.getElementById('cmd-overlay'))return;
  document.getElementById('cmd-overlay').classList.remove('open');
}
function renderCommands(cmds){
  const r=document.getElementById('cmd-results');
  if(cmds.length===0){r.innerHTML='<div class="cmd-empty">No results</div>';return}
  r.innerHTML=cmds.map((c,i)=>`<div class="cmd-item${i===0?' active':''}" onclick="commands[${commands.indexOf(c)}].action()">${c.icon}<span class="cmd-item-label">${c.label}</span>${c.kbd?`<span class="cmd-item-kbd">${c.kbd}</span>`:''}</div>`).join('');
}
function filterCommands(q){
  const filtered=commands.filter(c=>c.label.toLowerCase().includes(q.toLowerCase()));
  renderCommands(filtered);
}

// ============ Utils ============
function showToast(msg,type='info'){
  const c=document.getElementById('toast-container');const t=document.createElement('div');
  t.className=`toast toast-${type}`;
  const icons={success:'✓',error:'✗',info:'ℹ'};
  t.innerHTML=`<span>${icons[type]||'ℹ'}</span> ${escapeHtml(msg)}`;
  c.appendChild(t);setTimeout(()=>t.remove(),4000);
}
function escapeHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function sanitizeId(s){return s.replace(/[^a-zA-Z0-9]/g,'_')}
function formatBytes(b){if(b===0)return'0 B';const k=1024;const s=['B','KB','MB'];const i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]}
