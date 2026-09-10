let token = localStorage.getItem("nova_token");
let user = JSON.parse(localStorage.getItem("nova_user") || "null");
let conversationId = localStorage.getItem("nova_conversation") || crypto.randomUUID();
let attachment = null;
let recording = false;
let mediaRecorder = null;
let audioChunks = [];

const $ = id => document.getElementById(id);

function showLogin(){
  $("loginForm").classList.remove("hidden"); $("registerForm").classList.add("hidden");
  $("loginTab").classList.add("active"); $("registerTab").classList.remove("active");
}
function showRegister(){
  $("loginForm").classList.add("hidden"); $("registerForm").classList.remove("hidden");
  $("registerTab").classList.add("active"); $("loginTab").classList.remove("active");
}
function showApp(){
  $("auth").classList.add("hidden"); $("app").classList.remove("hidden");
  $("userName").textContent = user.name; $("userEmail").textContent = user.email;
  loadHistory();
}
function showAuth(){ $("auth").classList.remove("hidden"); $("app").classList.add("hidden"); }
function setError(text){ $("authError").textContent = text || ""; }

async function register(e){
  e.preventDefault(); setError("");
  const r = await fetch("/api/register",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({name:$("regName").value,email:$("regEmail").value,password:$("regPassword").value})});
  const d = await r.json(); if(!r.ok){setError(d.detail || "Registration failed");return;}
  token=d.token;user=d.user;localStorage.setItem("nova_token",token);localStorage.setItem("nova_user",JSON.stringify(user));showApp();
}
async function login(e){
  e.preventDefault(); setError("");
  const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({email:$("loginEmail").value,password:$("loginPassword").value})});
  const d=await r.json(); if(!r.ok){setError(d.detail || "Login failed");return;}
  token=d.token;user=d.user;localStorage.setItem("nova_token",token);localStorage.setItem("nova_user",JSON.stringify(user));showApp();
}
function logout(){localStorage.clear();location.reload();}
function authHeaders(){return {"Authorization":"Bearer "+token};}

async function loadHistory(){
  const r=await fetch("/api/history?conversation_id="+encodeURIComponent(conversationId),{headers:authHeaders()});
  if(!r.ok){logout();return;}
  const d=await r.json(); $("messages").innerHTML="";
  if(!d.messages.length){renderWelcome();return;}
  d.messages.forEach(m=>addMessage(m.role,m.content));
}
function renderWelcome(){
  $("messages").innerHTML='<div class="welcome"><div class="welcome-icon">✦</div><h1>How can I help you?</h1><p>Ask anything, upload an image or document, or use your voice.</p></div>';
}
function addMessage(role,text){
  const welcome=document.querySelector(".welcome"); if(welcome) welcome.remove();
  const div=document.createElement("div"); div.className="message "+(role==="user"?"user":"assistant");
  const avatar=role==="user"?"You":"✦";
  const html=role==="assistant" && window.marked ? marked.parse(text) : escapeHtml(text);
  div.innerHTML=`<div class="avatar">${avatar}</div><div class="bubble">${html}</div>`;
  $("messages").appendChild(div); $("messages").scrollTop=$("messages").scrollHeight;
}
function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}

async function sendMessage(e){
  e.preventDefault();
  const input=$("prompt"), message=input.value.trim(); if(!message && !attachment)return;
  if(message) addMessage("user",message);
  input.value=""; input.style.height="auto";
  const status=$("status"); status.textContent="Thinking…";
  let finalMessage=message;
  if(attachment && attachment.type==="document" && attachment.text){
    finalMessage += "\n\n[Uploaded document text]\n"+attachment.text;
  }
  const body={message:finalMessage||"Please analyze the uploaded image.",language:$("language").value,conversation_id:conversationId,
    image_data_url:attachment?.type==="image"?attachment.data_url:null};
  clearAttachment();
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{...authHeaders(),"Content-Type":"application/json"},body:JSON.stringify(body)});
    const d=await r.json(); if(!r.ok) throw new Error(d.detail||"Request failed");
    addMessage("assistant",d.answer);
  }catch(err){addMessage("assistant","Sorry, I couldn't complete that request: "+err.message);}
  status.textContent="Online";
}
function handleKey(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage(e)}}
$("prompt").addEventListener("input",()=>{$("prompt").style.height="auto";$("prompt").style.height=Math.min($("prompt").scrollHeight,160)+"px";});

$("fileInput").addEventListener("change",async()=>{
  const file=$("fileInput").files[0]; if(!file)return;
  $("attachmentName").textContent="Uploading "+file.name+"…"; $("attachment").classList.remove("hidden");
  const fd=new FormData();fd.append("file",file);
  try{
    const r=await fetch("/api/upload",{method:"POST",headers:authHeaders(),body:fd});
    const d=await r.json();if(!r.ok)throw new Error(d.detail||"Upload failed");
    attachment=d;$("attachmentName").textContent=file.name;
  }catch(err){clearAttachment();alert(err.message)}
});
function clearAttachment(){attachment=null;$("fileInput").value="";$("attachment").classList.add("hidden");}
function newChat(){conversationId=crypto.randomUUID();localStorage.setItem("nova_conversation",conversationId);renderWelcome();}

async function toggleRecording(){
  if(recording){mediaRecorder.stop();return;}
  if(!navigator.mediaDevices){alert("Microphone is not supported by this browser.");return;}
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    mediaRecorder=new MediaRecorder(stream);audioChunks=[];recording=true;$("micBtn").textContent="⏹";
    mediaRecorder.ondataavailable=e=>audioChunks.push(e.data);
    mediaRecorder.onstop=async()=>{
      recording=false;$("micBtn").textContent="🎤";stream.getTracks().forEach(t=>t.stop());
      const blob=new Blob(audioChunks,{type:"audio/webm"});
      const fd=new FormData();fd.append("audio",blob,"recording.webm");
      try{
        const r=await fetch("/api/transcribe",{method:"POST",headers:authHeaders(),body:fd});
        const d=await r.json();if(!r.ok)throw new Error(d.detail||"Transcription failed");
        $("prompt").value=d.text;
        $("prompt").dispatchEvent(new Event("input"));
      }catch(err){alert(err.message)}
    };
    mediaRecorder.start();
  }catch(err){alert("Microphone permission was denied or unavailable.");}
}

document.addEventListener("click",async e=>{
  const button=e.target.closest(".assistant .bubble");
  if(button && e.target.tagName==="BUTTON") return;
});

if(token && user) showApp(); else showAuth();
