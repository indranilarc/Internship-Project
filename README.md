# 🧠 RAG Intelligence Hub

### AI-Powered Document Question Answering System

RAG Intelligence Hub is a local Retrieval-Augmented Generation (RAG) application that allows users to upload documents and ask questions about their contents.

Instead of sending the entire document directly to an AI model, the application extracts the document text, divides it into smaller chunks, converts those chunks into vector embeddings, searches for the most relevant information using FAISS, and finally sends the retrieved context to an LLM to generate a grounded answer.

The project provides a modern dark navy and neon-green web interface for interacting with the RAG system.

---

## ✨ Features

- 📄 Upload PDF and TXT documents
- 🔍 Extract text from uploaded documents
- ✂️ Split documents into smaller chunks
- 🧠 Generate semantic embeddings
- ⚡ Perform similarity search using FAISS
- 🤖 Generate answers using an LLM
- 💬 Interactive document question-answering interface
- 🌐 Local RAG processing
- 🎨 Modern dark navy + neon UI
- 📱 Responsive interface
- 🔒 Documents can be processed locally

---

# 🚀 How RAG Works

The application follows a simple RAG pipeline:

```text
             DOCUMENT
                 │
                 ▼
        ┌─────────────────┐
        │  Text Extraction│
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │     Chunking    │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    Embeddings   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │      FAISS      │
        │ Vector Database │
        └────────┬────────┘
                 │
                 │ Relevant Context
                 ▼
             USER QUERY
                 │
                 ▼
        ┌─────────────────┐
        │   Retrieval     │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │       LLM       │
        └────────┬────────┘
                 │
                 ▼
              ANSWER
