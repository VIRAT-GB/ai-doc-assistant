# AI Doc Assistant

AI Doc Assistant is a Flask-based web application that allows users to upload PDF documents, ask questions about their documents, and generate summaries.

The project includes user authentication, document isolation, PDF text extraction, keyword-based document retrieval, question answering, and chat history.


## Live Demo

https://ai-doc-assistant-q56n.onrender.com


## GitHub


https://github.com/VIRAT-GB/ai-doc-assistant

## Features

- User registration and login
- Secure password hashing
- User-specific document isolation
- PDF document upload
- PDF text extraction
- Automatic document chunking
- Keyword-based document search
- Ask questions about uploaded documents
- AI-style extractive answers based on document content
- Document summaries
- Chat history
- Open and delete uploaded documents
- Protected routes using Flask-Login
- Responsive web interface

## Tech Stack

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- pypdf
- Markdown
- HTML
- CSS
- Gunicorn
- Git & GitHub
- Render

## Project Architecture

The application follows a simple Flask web application architecture.

### Document Processing

1. User uploads a PDF.
2. The PDF text is extracted using `pypdf`.
3. The extracted text is divided into smaller chunks.
4. Chunks are stored and associated with the logged-in user.
5. When the user asks a question, the application searches the document chunks for relevant keywords.
6. The most relevant text is used to generate an answer.

### User Isolation

Each document is associated with the user who uploaded it using `user_id`.

This prevents one user from accessing another user's uploaded documents.

### Database

SQLite with SQLAlchemy is used to manage:

- Users
- Documents
- Chat history

## Application Flow

```text
User
  ↓
Login / Register
  ↓
Upload PDF
  ↓
Extract PDF Text
  ↓
Split into Chunks
  ↓
Store Document
  ↓
Ask Question
  ↓
Search Relevant Chunks
  ↓
Generate Answer
  ↓
Display Answer + Chat History
```

## Project Structure

```text
ai-doc-assistant/
│
├── app.py
├── models.py
├── requirements.txt
├── readme.md
├── .gitignore
│
├── templates/
│   ├── index.html
│   ├── login.html
│   └── register.html
│
└── static/
    └── style.css
```

## Running Locally

Clone the repository:

```bash
git clone https://github.com/VIRAT-GB/ai-doc-assistant.git
cd ai-doc-assistant
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Deployment

The application is deployed on Render using Gunicorn.

Start command:

```bash
gunicorn app:app
```

The deployed version is designed to run within the resource limits of the Render deployment environment and does not depend on large machine-learning libraries or a locally running Ollama server.

## What I Learned

Through this project, I worked with:

- Flask application development
- Authentication and authorization
- Password hashing
- SQLAlchemy database models
- SQLite
- PDF processing
- Text chunking
- Document retrieval
- User-specific data isolation
- REST-style Flask routes
- HTML/CSS frontend development
- Git and GitHub
- Production deployment with Gunicorn
- Render deployment
- Debugging deployment and memory issues

## Future Improvements

Possible future improvements include:

- Vector embeddings
- Semantic search
- Retrieval-Augmented Generation (RAG)
- Larger language models
- Streaming AI responses
- Improved document processing
- Support for additional document formats
- Cloud database integration