from pathlib import Path
import uuid
import requests
import numpy as np
import faiss

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI-Powered RAG Document Assistant")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Sentence Transformers model used for chunk embeddings.
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# In-memory RAG state for this student project.
documents = {}  # document_id -> metadata/chunks
faiss_indexes = {}  # document_id -> FAISS index

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


class QuestionRequest(BaseModel):
    document_id: str
    question: str


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError("Only PDF and TXT files are supported.")


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150):
    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def build_index(document_id: str, chunks: list[str]):
    vectors = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss_indexes[document_id] = index


def ask_ollama(question: str, context: str) -> str:
    prompt = f"""
You are a document question-answering assistant.

Answer ONLY using the context below.
If the answer is not present in the context, say:
"Information not found in the uploaded document."

Keep the answer clear and concise.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
""".strip()

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.RequestException:
        raise RuntimeError(
            "Ollama is not running. Start Ollama and make sure the "
            f"'{OLLAMA_MODEL}' model is installed."
        )


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail="Upload a PDF or TXT file.")

    document_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}{extension}"
    saved_path.write_bytes(await file.read())

    try:
        text = extract_text(saved_path)
    except Exception as exc:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    chunks = chunk_text(text)
    if not chunks:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="No readable text was found.")

    build_index(document_id, chunks)
    documents[document_id] = {
        "filename": filename,
        "chunks": chunks,
        "characters": len(text),
    }

    return {
        "document_id": document_id,
        "filename": filename,
        "chunks": len(chunks),
        "characters": len(text),
        "message": "Document processed and indexed successfully."
    }


@app.post("/api/ask")
def ask_question(request: QuestionRequest):
    if request.document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found.")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question.")

    doc = documents[request.document_id]
    query_vector = embedding_model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    index = faiss_indexes[request.document_id]
    k = min(4, len(doc["chunks"]))
    scores, ids = index.search(query_vector, k)

    retrieved = []
    for score, idx in zip(scores[0], ids[0]):
        if idx >= 0:
            retrieved.append({
                "chunk": doc["chunks"][int(idx)],
                "score": float(score)
            })

    # Low similarity means the requested information is probably not in the file.
    if not retrieved or max(x["score"] for x in retrieved) < 0.25:
        return {
            "answer": "Information not found in the uploaded document.",
            "sources": []
        }

    context = "\n\n---\n\n".join(x["chunk"] for x in retrieved)

    try:
        answer = ask_ollama(question, context)
    except RuntimeError as exc:
        # Useful fallback for demonstration when Ollama is not available.
        answer = (
            "LLM unavailable: "
            + str(exc)
            + "\n\nRetrieved document context:\n"
            + context
        )

    return {
        "answer": answer,
        "sources": [
            {
                "score": round(x["score"], 3),
                "text": x["chunk"][:260] + ("..." if len(x["chunk"]) > 260 else "")
            }
            for x in retrieved
        ]
    }
