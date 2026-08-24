const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const fileInfo = document.getElementById("fileInfo");
const uploadBtn = document.getElementById("uploadBtn");
const question = document.getElementById("question");
const askBtn = document.getElementById("askBtn");
const chat = document.getElementById("chat");
const documentLabel = document.getElementById("documentLabel");

let selectedFile = null;
let documentId = null;

function chooseFile(file) {
  if (!file) return;
  const ext = file.name.toLowerCase().split(".").pop();
  if (!["pdf", "txt"].includes(ext)) {
    alert("Please choose a PDF or TXT file.");
    return;
  }
  selectedFile = file;
  fileInfo.classList.remove("hidden");
  fileInfo.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
  uploadBtn.disabled = false;
}

fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));
["dragenter", "dragover"].forEach(e => dropzone.addEventListener(e, ev => {
  ev.preventDefault(); dropzone.classList.add("drag");
}));
["dragleave", "drop"].forEach(e => dropzone.addEventListener(e, ev => {
  ev.preventDefault(); dropzone.classList.remove("drag");
}));
dropzone.addEventListener("drop", ev => chooseFile(ev.dataTransfer.files[0]));

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  uploadBtn.disabled = true;
  uploadBtn.textContent = "Processing…";

  const form = new FormData();
  form.append("file", selectedFile);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed.");

    documentId = data.document_id;
    documentLabel.textContent = `${data.filename} · ${data.chunks} chunks indexed`;
    question.disabled = false;
    askBtn.disabled = false;
    uploadBtn.textContent = "Document ready ✓";
    addMessage("assistant",
      `I've processed "${data.filename}". I created ${data.chunks} text chunks and indexed their embeddings. Ask me anything about the document.`);
  } catch (err) {
    alert(err.message);
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Process document";
  }
});

askBtn.addEventListener("click", ask);
question.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    ask();
  }
});

async function ask() {
  const q = question.value.trim();
  if (!q || !documentId) return;

  addMessage("user", q);
  question.value = "";
  askBtn.disabled = true;
  addMessage("assistant", "Searching the document and generating an answer…", "loading");

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ document_id: documentId, question: q })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Question failed.");

    const loading = chat.querySelector(".loading");
    if (loading) loading.closest(".message").remove();

    let sourceText = "";
    if (data.sources?.length) {
      sourceText = `Retrieved ${data.sources.length} relevant chunk(s) · best similarity ${data.sources[0].score}`;
    }
    addMessage("assistant", data.answer, sourceText);
  } catch (err) {
    const loading = chat.querySelector(".loading");
    if (loading) loading.closest(".message").remove();
    addMessage("assistant", `Error: ${err.message}`);
  } finally {
    askBtn.disabled = false;
    question.focus();
  }
}

function addMessage(role, text, source = "") {
  const welcome = chat.querySelector(".welcome");
  if (welcome) welcome.remove();

  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (source === "loading") bubble.classList.add("loading");
  bubble.textContent = text;
  wrap.appendChild(bubble);

  if (source && source !== "loading") {
    const s = document.createElement("div");
    s.className = "source";
    s.textContent = source;
    wrap.appendChild(s);
  }
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}