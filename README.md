# Pinnacle---Backend ![Node.js](https://img.shields.io/badge/Node.js-20.5.1-green) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0-blue) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14.4-blue) ![Redis](https://img.shields.io/badge/Redis-7.0.11-blue) ![Supabase](https://img.shields.io/badge/Supabase-1.35.4-blue) ![OpenAI](https://img.shields.io/badge/OpenAI-0.27.8-blue)

---

## 📖 Introduction

**Pinnacle---Backend** is a robust, modern backend API designed to power a web content organization and retrieval platform. Built with FastAPI (Python) for high performance, it integrates with Supabase for data storage, Redis for task queuing, and various LLM providers for AI-driven features. The system allows users to save, organize, and search web content, including articles, videos, images, and more. It supports content extraction, transcription, OCR, embeddings, and retrieval-augmented generation (RAG) to enable intelligent, context-aware conversations and content management.

This backend serves as the core API layer for a comprehensive knowledge management platform, with features tailored for seamless content ingestion, deduplication, embedding generation, and conversational AI, all orchestrated through well-structured REST API endpoints.

---

## ✨ Features

- **User Authentication & Profile Management:** Secure sign-up, login, and profile customization.
- **Content Saving & Organization:** Save bookmarks, articles, videos, and images with tags, folders, and notes.
- **Content Extraction & Transcription:** Automatic extraction of webpage content, audio/video transcription, and OCR for images.
- **Duplicate Detection:** Prevent duplicate entries via URL-based deduplication.
- **Embeddings & Vector Search:** Generate and store vector embeddings for semantic search and retrieval.
- **Retrieval-Augmented Generation (RAG):** Context-aware chat responses leveraging relevant stored content.
- **Content Sharing:** Generate shareable links for saved items.
- **Background Processing:** Content extraction, transcription, and OCR handled asynchronously via queues.
- **Extensible LLM Support:** Multi-provider LLM configuration with fallback options.
- **Configurable Features & Security:** Feature flags, secret management, CORS, and token expiry controls.

---

## 🛠️ Tech Stack

| Technology / Library             | Purpose                                                      | Version / Details                                    |
|----------------------------------|--------------------------------------------------------------|-----------------------------------------------------|
| **FastAPI**                     | API framework for high-performance REST API                | 0.100.0                                            |
| **Python**                      | Programming language                                       | 3.11                                               |
| **Uvicorn**                     | ASGI server for FastAPI                                    | 0.26.0                                             |
| **Loguru**                      | Logging and debugging                                      | 0.7.0                                              |
| **Pydantic (pydantic-settings)**| Settings management, data validation                         | 2.2.0                                              |
| **Supabase (Python SDK)**       | Database and auth via Postgres + Auth API                  | 1.35.4                                             |
| **Redis (Async client)**        | Queues and caching                                         | 4.5.5                                              |
| **OpenAI API**                  | LLM provider                                               | 0.27.8                                             |
| **Various LLM APIs**             | Support for multiple providers (Groq, Google, Euron, Mistral, OpenRouter) | Version varies, configured via env           |
| **Tesseract OCR**               | Optical Character Recognition for images                   | Path configured in `app/config.py` (`/usr/bin/tesseract`) |
| **Web Content Extraction**      | Custom extraction via `extraction_service`                 | Implemented in code, handles URL content parsing |
| **Background Tasks & Queues**   | Async processing of content extraction, transcription, OCR | Custom queue_service with Redis backend        |

*(Note: No front-end libraries are included in this backend repo; the project focuses solely on the API layer.)*

---

## 🚀 Quick Start / Installation

```bash
# Clone the repository
git clone https://github.com/uzumaki-ak/Pinnacle---Backend (36 files.git

# Navigate into the project directory
cd Pinnacle---Backend

# Create a virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env as needed with your database, API keys, and config

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*(Note: If you prefer Docker, ensure your `Dockerfile` and `docker-compose.yml` are configured accordingly, then run `docker-compose up`.)*

---

## 📁 Project Structure

```
/app
│
├── config.py               # Configuration settings and environment variables
├── main.py                 # FastAPI application setup and startup events
├── routes/                 # API route definitions (auth, items, chat, extract, share)
│   ├── __init__.py
│   ├── auth.py
│   ├── items.py
│   ├── chat.py
│   ├── extract.py
│   └── share.py
├── models/                 # Pydantic schemas for data validation
│   ├── __init__.py
│   ├── item.py
│   ├── user.py
│   └── embedding.py
├── services/               # Business logic and integrations (LLM, embeddings, vector DB, queue)
│   ├── __init__.py
│   ├── llm_service.py
│   ├── embedding_service.py
│   ├── vector_service.py
│   ├── extraction_service.py
│   ├── transcription_service.py
│   ├── ocr_service.py
│   └── queue_service.py
├── workers/                # Background worker scripts for extraction, transcription, OCR
│   └── extraction_worker.py
└── utils/                  # Utility functions and helpers
    ├── __init__.py
    ├── youtube.py
    ├── deduplication.py
    └── validators.py
```

*Each folder is dedicated to a specific concern: configuration, API routes, data schemas, background tasks, and utilities.*

---

## 🔧 Configuration

- **Environment Variables (.env):**
  - `SUPABASE_URL`: Your Supabase project URL
  - `SUPABASE_SERVICE_KEY`: Service role API key for database access
  - `API_VERSION`: API versioning (default: `v1`)
  - `PORT`: Server port (default: `8000`)
  - `SECRET_KEY`: JWT secret for token signing
  - `ALGORITHM`: JWT algorithm (default: `HS256`)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiry in minutes (default: `1440`)
  - `REDIS_URL`: Redis server URL (default: `redis://localhost:6379`)
  - `TESSERACT_PATH`: Path to Tesseract OCR binary (`/usr/bin/tesseract`)
  - API keys for LLM providers (`GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, etc.)
  - Feature flags (`ENABLE_AUTO_TRANSCRIPTION`, `ENABLE_AUTO_OCR`, etc.)

- **Config Files:**
  - `app/config.py`: Handles loading env variables via `pydantic-settings`
  - `tailwind.config.js`, `next.config.js` are not used; focus is on backend API

---

## 🌲 Project Structure Overview

- `/app`: Core application code, including configuration, routes, models, and services
- `/routes`: Defines REST API endpoints for authentication, content items, chat, extraction, sharing
- `/models`: Pydantic schemas for request/response validation
- `/services`: Business logic for LLM, embeddings, vector database, background processing
- `/workers`: Background workers for long-running tasks (extraction, transcription, OCR)
- `/utils`: Helper functions for URL validation, deduplication, YouTube transcript extraction

---

## 🔑 API Reference (Examples)

### Authentication
- **POST /auth/login**: Authenticate user and generate JWT token
- **POST /auth/register**: Register new user

### Content Items
- **POST /items/**: Save a new content item
- **GET /items/{id}**: Retrieve item details
- **PATCH /items/{id}**: Update item
- **DELETE /items/{id}**: Delete item

### Chat
- **POST /chat/message**: Send message with optional RAG context
  - *Request body sample:*
    ```json
    {
      "messages": [{"role": "user", "content": "Tell me about AI"}],
      "temperature": 0.7,
      "max_tokens": 1000,
      "use_rag": true
    }
    ```

### Content Extraction
- **POST /extract/content**: Extract webpage content
- **POST /extract/transcript**: Transcribe video/audio URL
- **POST /extract/ocr**: OCR from image URL

*(Full API docs can be generated with FastAPI's automatic docs at `/docs`)*

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Thanks to the open-source community for FastAPI, Supabase, and Redis.
- Special thanks to contributors and testers helping improve platform features.
- Inspired by modern content management and AI-driven knowledge platforms.

---

*This README provides a detailed, accurate overview of Pinnacle---Backend based solely on the codebase and project structure. For further details, refer to the source code and API documentation.*
