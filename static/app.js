const translations = {
  en: {
    tagline:"Your farming companion",local:"Local AI",eyebrow:"AGRICULTURE • WEATHER • GOVERNMENT POLICIES",
    heading:"How can I help your farm today?",subheading:"Ask in Hindi or English about crops, mandi prices, weather forecasts or government policies.",
    assistant:"Ask Gram Sahayak",assistantDesc:"Your AI agricultural assistant",
    hello:"Namaste! I can help with farming questions, live mandi prices, weather forecasts and policy documents. What would you like to know?",
    weatherChip:"7-day weather",mandiChip:"Mandi prices",cropChip:"Crop advice",
    placeholder:"Type your question in Hindi or English...",send:"Send",privacy:"Your questions are processed using your local Ollama model.",
    documents:"Policy documents",documentsDesc:"Upload and understand a government policy",uploadTitle:"Upload a document",
    uploadHint:"PDF, DOCX or TXT · Max 15 MB",noFile:"No document uploaded",summarize:"Summarize policy",
    tools:"What I can do",marketTitle:"Mandi prices",marketDesc:"Daily market rates from data.gov.in",
    weatherTitle:"Weather forecast",weatherDesc:"Current conditions and 7-day forecast",
    policyTitle:"Policy understanding",policyDesc:"Simple summaries of uploaded documents",
    farmTitle:"Farming guidance",farmDesc:"Crop, soil and irrigation suggestions",
    footer:"Built for accessible agricultural information",uploading:"Uploading document…",uploaded:"Document ready",
    thinking:"Thinking…",uploadFailed:"Upload failed",summaryWorking:"Preparing policy summary…",
    summaryDone:"Policy summary",empty:"Please type a question first.",error:"Something went wrong"
  },
  hi: {
    tagline:"आपका खेती साथी",local:"लोकल एआई",eyebrow:"कृषि • मौसम • सरकारी योजनाएँ",
    heading:"आज मैं आपकी खेती में कैसे मदद कर सकता हूँ?",subheading:"फसल, मंडी भाव, मौसम पूर्वानुमान या सरकारी नीतियों के बारे में हिंदी या अंग्रेज़ी में पूछें।",
    assistant:"ग्राम सहायक से पूछें",assistantDesc:"आपका एआई कृषि सहायक",
    hello:"नमस्ते! मैं खेती, मंडी भाव, मौसम पूर्वानुमान और सरकारी नीति दस्तावेज़ों के बारे में मदद कर सकता हूँ। आप क्या जानना चाहते हैं?",
    weatherChip:"7 दिन का मौसम",mandiChip:"मंडी भाव",cropChip:"फसल सलाह",
    placeholder:"हिंदी या अंग्रेज़ी में अपना सवाल लिखें...",send:"भेजें",privacy:"आपके सवाल आपके लोकल Ollama मॉडल से प्रोसेस होते हैं।",
    documents:"नीति दस्तावेज़",documentsDesc:"सरकारी नीति अपलोड करें और समझें",uploadTitle:"दस्तावेज़ अपलोड करें",
    uploadHint:"PDF, DOCX या TXT · अधिकतम 15 MB",noFile:"कोई दस्तावेज़ अपलोड नहीं है",summarize:"नीति का सारांश",
    tools:"मैं क्या कर सकता हूँ",marketTitle:"मंडी भाव",marketDesc:"data.gov.in से दैनिक मंडी दरें",
    weatherTitle:"मौसम पूर्वानुमान",weatherDesc:"वर्तमान मौसम और 7 दिन का पूर्वानुमान",
    policyTitle:"नीति की जानकारी",policyDesc:"अपलोड किए दस्तावेज़ों का सरल सारांश",
    farmTitle:"खेती संबंधी सलाह",farmDesc:"फसल, मिट्टी और सिंचाई सुझाव",
    footer:"कृषि जानकारी को आसान बनाने के लिए",uploading:"दस्तावेज़ अपलोड हो रहा है…",uploaded:"दस्तावेज़ तैयार है",
    thinking:"सोच रहा हूँ…",uploadFailed:"अपलोड विफल",summaryWorking:"नीति का सारांश बनाया जा रहा है…",
    summaryDone:"नीति का सारांश",empty:"कृपया पहले सवाल लिखें।",error:"कुछ गलत हुआ"
  }
};
let lang = "en", documentId = null, documentName = "";
const $ = id => document.getElementById(id);
function t(key){return translations[lang][key] || translations.en[key] || key}
function applyLanguage(){
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => el.placeholder = t(el.dataset.i18nPlaceholder));
  $("language").value = lang;
}
function addMessage(text, who="assistant"){
  const row=document.createElement("div"); row.className=`message ${who==="user"?"user-message":"assistant-message"}`;
  const avatar=document.createElement("div"); avatar.className="avatar"; avatar.textContent=who==="user"?"👤":"🌱";
  const bubble=document.createElement("div"); bubble.className="bubble"; bubble.textContent=text;
  row.append(avatar,bubble); $("messages").append(row); $("messages").scrollTop=$("messages").scrollHeight;
  return bubble;
}
async function sendMessage(text){
  text=(text||"").trim(); if(!text){addMessage(t("empty"));return}
  addMessage(text,"user"); $("messageInput").value="";
  const pending=addMessage(t("thinking")); $("sendBtn").disabled=true;
  try{
    const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,language:lang,document_id:documentId})});
    const data=await res.json(); if(!res.ok) throw new Error(data.detail||t("error"));
    pending.textContent=data.answer;
    if("speechSynthesis" in window) { /* speech is user-triggered only */ }
  }catch(e){pending.textContent=`${t("error")}: ${e.message}`}
  finally{$("sendBtn").disabled=false}
}
$("language").addEventListener("change",e=>{lang=e.target.value;applyLanguage()});
$("chatForm").addEventListener("submit",e=>{e.preventDefault();sendMessage($("messageInput").value)});
$("clearChat").addEventListener("click",()=>{$("messages").innerHTML="";addMessage(t("hello"))});
document.querySelectorAll(".suggestion").forEach(btn=>btn.addEventListener("click",()=>sendMessage(lang==="hi"?btn.dataset.promptHi:btn.dataset.promptEn)));
$("fileInput").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  $("fileStatus").textContent=t("uploading");
  const form=new FormData();form.append("file",file);form.append("language",lang);
  try{
    const res=await fetch("/api/upload",{method:"POST",body:form});const data=await res.json();if(!res.ok)throw new Error(data.detail||t("uploadFailed"));
    documentId=data.document_id;documentName=data.filename;$("fileStatus").textContent=`✓ ${data.filename} (${data.characters.toLocaleString()} characters)`;$("summaryBtn").disabled=false;
  }catch(err){$("fileStatus").textContent=`${t("uploadFailed")}: ${err.message}`;documentId=null;$("summaryBtn").disabled=true}
});
$("summaryBtn").addEventListener("click",async()=>{
  if(!documentId)return;
  $("summaryBtn").disabled=true;const pending=addMessage(t("summaryWorking"));
  const form=new FormData();form.append("document_id",documentId);form.append("language",lang);
  try{const res=await fetch("/api/document/summary",{method:"POST",body:form});const data=await res.json();if(!res.ok)throw new Error(data.detail||t("error"));pending.textContent=`${t("summaryDone")}: ${documentName}\n\n${data.answer}`}
  catch(e){pending.textContent=`${t("error")}: ${e.message}`}
  finally{$("summaryBtn").disabled=false}
});
$("voiceBtn").addEventListener("click",()=>{
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition){addMessage(lang==="hi"?"आपके ब्राउज़र में वॉइस इनपुट उपलब्ध नहीं है। Chrome या Edge का उपयोग करें।":"Voice input is not available in this browser. Please use Chrome or Edge.");return}
  const recognition=new SpeechRecognition();recognition.lang=lang==="hi"?"hi-IN":"en-IN";recognition.interimResults=false;
  recognition.onresult=e=>{$("messageInput").value=e.results[0][0].transcript;$("messageInput").focus()};
  recognition.onerror=()=>addMessage(lang==="hi"?"माइक्रोफ़ोन की अनुमति जाँचें।":"Please check microphone permission.");
  recognition.start();
});
applyLanguage();
