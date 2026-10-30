# AI Doc Assistant

AI Doc Assistant is a Flask-based web application that allows users to upload PDF documents and ask questions about their content using AI.

The application extracts text from uploaded PDFs, splits the text into smaller chunks, creates semantic embeddings, finds the most relevant parts of the document, and uses a local LLM to generate an answer based on the retrieved content.

## Features

- User registration and login
- Secure password hashing
- User-specific document isolation
- PDF upload
- Secure PDF file storage
- PDF text extraction
- Text chunking
- Semantic embeddings
- Semantic similarity search
- Retrieval-Augmented Generation (RAG)
- Local AI responses using Ollama
- Conversation-aware questions
- Chat history
- AI-generated document summaries
- Source page references
- Document deletion
- Responsive web interface
- 10 MB PDF upload limit
- PDF-only file validation

## How It Works

```text
PDF Upload
    ↓
PDF Text Extraction
    ↓
Text Chunking
    ↓
Sentence Transformer Embeddings
    ↓
User Question
    ↓
Question Embedding
    ↓
Semantic Similarity Search
    ↓
Relevant Document Chunks
    ↓
Conversation Context
    ↓
Ollama LLM
    ↓
AI Answer + Source Pages
```

## Technology Stack

### Backend
- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login

### AI / Machine Learning
- Sentence Transformers
- `all-MiniLM-L6-v2`
- Ollama
- Llama 3.2 3B
- NumPy
- Retrieval-Augmented Generation (RAG)

### PDF Processing
- pypdf

### Database
- SQLite
- SQLAlchemy

### Frontend
- HTML
- CSS
- JavaScript

### Development Tools
- Git
- GitHub
- VS Code

## Security

The application includes several basic security measures:

- Passwords are stored using secure password hashing.
- Users can only access their own documents.
- Uploaded files are restricted to PDF files.
- Uploaded files have a maximum size of 10 MB.
- Uploaded files are stored using unique internal filenames.
- Sensitive files such as `.env`, uploaded documents, the virtual environment, and the SQLite database are excluded from Git.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/VIRAT-GB/ai-doc-assistant.git
cd ai-doc-assistant
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install and run Ollama

Install Ollama on your computer and download the required model:

```bash
ollama pull llama3.2:3b
```

Make sure Ollama is running before starting the Flask application.

### 6. Start the application

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Example

A user can upload a resume PDF and ask:

> What is my B.Tech CGPA?

The application retrieves the most relevant section of the PDF and generates an answer using the local LLM.

## Project Structure

```text
ai-doc-assistant/
│
├── app.py
├── models.py
├── requirements.txt
├── README.md
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

## Key Concepts Demonstrated

This project demonstrates practical implementation of:

- Flask web development
- User authentication
- Database operations with SQLAlchemy
- PDF processing
- Text preprocessing
- Embeddings
- Vector similarity
- Semantic search
- Retrieval-Augmented Generation
- Local LLM integration
- Prompt construction
- Conversation context
- Secure file handling
- Git and GitHub

## Future Deployment

The application is designed to be deployed as a production web application. The local Ollama setup is currently used for AI inference during development.

## Author

**GB Virat**

B.Tech Electronics and Communication Engineering  
PES University, Bengaluru

GitHub: https://github.com/VIRAT-GB