import os
import uuid
import numpy as np
import ollama

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import markdown

from models import db, User, Document, ChatHistory


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "ai-doc-assistant-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///documents.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Maximum upload size = 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# UPLOAD FOLDER
# ============================================================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    "pdf"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

db.init_app(app)


# ============================================================
# LOGIN MANAGER
# ============================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please login to continue."


# ============================================================
# LOAD LOGGED-IN USER
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# ============================================================
# EMBEDDING MODEL
# ============================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded successfully.")


# ============================================================
# TEXT CHUNKING
# ============================================================

def split_text(
    text,
    chunk_size=500,
    overlap=100
):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():

            chunks.append(chunk)

        start = end - overlap

    return chunks


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    vector1,
    vector2
):

    vector1 = np.array(vector1)

    vector2 = np.array(vector2)

    denominator = (
        np.linalg.norm(vector1)
        *
        np.linalg.norm(vector2)
    )

    if denominator == 0:

        return 0

    similarity = np.dot(
        vector1,
        vector2
    ) / denominator

    return similarity


# ============================================================
# DOCUMENT LOADER
# ============================================================

def load_document(document):

    # New documents use stored_filename.
    #
    # Existing documents created before this feature
    # still have stored_filename = NULL.
    #
    # In that case, use the original filename.

    filename = (
        document.stored_filename
        or document.filename
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            "The document file could not be found."
        )

    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        text = page.extract_text()

        if text:

            pages.append(
                {
                    "page": page_number,
                    "text": text
                }
            )

    return pages


# ============================================================
# CHAT HISTORY
# ============================================================

def get_chat_history(document_id):

    return ChatHistory.query.filter_by(
        document_id=document_id
    ).order_by(
        ChatHistory.created_at.asc()
    ).all()


# ============================================================
# BUILD CONVERSATION CONTEXT
# ============================================================

def build_conversation_context(document_id):

    history = ChatHistory.query.filter_by(
        document_id=document_id
    ).order_by(
        ChatHistory.created_at.desc()
    ).limit(5).all()

    history.reverse()

    if not history:

        return "No previous conversation."

    conversation = []

    for item in history:

        conversation.append(
            f"User: {item.question}"
        )

        conversation.append(
            f"Assistant: {item.answer}"
        )

    return "\n".join(conversation)


# ============================================================
# HOME / DASHBOARD
# ============================================================

@app.route("/")
@login_required
def home():

    documents = Document.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Document.upload_date.desc()
    ).all()

    return render_template(
        "index.html",
        documents=documents,
        current_document=None
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # --------------------------------------------
        # VALIDATE USERNAME
        # --------------------------------------------

        if not username:

            flash(
                "Username is required.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # --------------------------------------------
        # VALIDATE PASSWORD
        # --------------------------------------------

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # --------------------------------------------
        # CONFIRM PASSWORD
        # --------------------------------------------

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # --------------------------------------------
        # CHECK EXISTING USER
        # --------------------------------------------

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # --------------------------------------------
        # CREATE USER
        # --------------------------------------------

        hashed_password = generate_password_hash(
            password
        )

        user = User(
            username=username,
            password_hash=hashed_password
        )

        db.session.add(user)

        db.session.commit()

        flash(
            "Account created successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            login_user(user)

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("home")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@app.route(
    "/upload",
    methods=["POST"]
)
@login_required
def upload():

    file = request.files.get(
        "file"
    )

    # --------------------------------------------
    # CHECK FILE
    # --------------------------------------------

    if not file:

        flash(
            "Please select a PDF file.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    if not file.filename:

        flash(
            "Please select a PDF file.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    # --------------------------------------------
    # CHECK FILE TYPE
    # --------------------------------------------

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only PDF files are allowed.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    # --------------------------------------------
    # SECURE ORIGINAL FILENAME
    # --------------------------------------------

    original_filename = secure_filename(
        file.filename
    )

    if not original_filename:

        flash(
            "Invalid filename.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    # --------------------------------------------
    # CREATE UNIQUE INTERNAL FILENAME
    # --------------------------------------------

    file_extension = os.path.splitext(
        original_filename
    )[1].lower()

    unique_filename = (
        f"{uuid.uuid4().hex}"
        f"{file_extension}"
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    # --------------------------------------------
    # SAVE FILE
    # --------------------------------------------

    file.save(
        file_path
    )

    try:

        # ----------------------------------------
        # CREATE DOCUMENT RECORD
        # ----------------------------------------

        document = Document(
            filename=original_filename,
            stored_filename=unique_filename,
            user_id=current_user.id
        )

        db.session.add(
            document
        )

        db.session.flush()

        # ----------------------------------------
        # EXTRACT PDF TEXT
        # ----------------------------------------

        pages = load_document(
            document
        )

        full_text = "\n".join(
            page["text"]
            for page in pages
        )

        if not full_text.strip():

            db.session.rollback()

            if os.path.exists(file_path):

                os.remove(file_path)

            flash(
                "Could not extract text from this PDF.",
                "error"
            )

            return redirect(
                url_for("home")
            )

        # ----------------------------------------
        # CREATE CHUNKS
        # ----------------------------------------

        chunks = split_text(
            full_text
        )

        document.chunk_count = len(
            chunks
        )

        # ----------------------------------------
        # CREATE EMBEDDINGS
        # ----------------------------------------

        if chunks:

            embedding_model.encode(
                chunks
            )

        # ----------------------------------------
        # SAVE DATABASE
        # ----------------------------------------

        db.session.commit()

        flash(
            f"'{original_filename}' uploaded successfully.",
            "success"
        )

    except Exception as error:

        db.session.rollback()

        if os.path.exists(file_path):

            os.remove(file_path)

        print(
            "Upload error:",
            error
        )

        flash(
            "Something went wrong while processing the PDF.",
            "error"
        )

    return redirect(
        url_for("home")
    )


# ============================================================
# OPEN DOCUMENT
# ============================================================

@app.route(
    "/open/<int:document_id>"
)
@login_required
def open_document(document_id):

    document = Document.query.get_or_404(
        document_id
    )

    # --------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------

    if document.user_id != current_user.id:

        flash(
            "You are not allowed to access this document.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    documents = Document.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Document.upload_date.desc()
    ).all()

    return render_template(
        "index.html",
        documents=documents,
        current_document=document
    )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.route(
    "/delete/<int:document_id>"
)
@login_required
def delete_document(document_id):

    document = Document.query.get_or_404(
        document_id
    )

    # --------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------

    if document.user_id != current_user.id:

        flash(
            "You are not allowed to delete this document.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    # --------------------------------------------
    # DELETE PHYSICAL FILE
    # --------------------------------------------

    filename = (
        document.stored_filename
        or document.filename
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.exists(file_path):

        try:

            os.remove(file_path)

        except Exception as error:

            print(
                "File deletion error:",
                error
            )

    # --------------------------------------------
    # DELETE CHAT HISTORY
    # --------------------------------------------

    ChatHistory.query.filter_by(
        document_id=document.id
    ).delete()

    # --------------------------------------------
    # DELETE DOCUMENT RECORD
    # --------------------------------------------

    db.session.delete(
        document
    )

    db.session.commit()

    flash(
        "Document deleted successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# ASK AI
# ============================================================

@app.route(
    "/ask",
    methods=["POST"]
)
@login_required
def ask():

    document_id = request.form.get(
        "document_id"
    )

    question = request.form.get(
        "question",
        ""
    ).strip()

    # --------------------------------------------
    # VALIDATE QUESTION
    # --------------------------------------------

    if not document_id:

        flash(
            "Please select a document first.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    if not question:

        flash(
            "Please enter a question.",
            "error"
        )

        return redirect(
            url_for(
                "open_document",
                document_id=document_id
            )
        )

    # --------------------------------------------
    # FIND DOCUMENT
    # --------------------------------------------

    document = Document.query.get_or_404(
        int(document_id)
    )

    # --------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------

    if document.user_id != current_user.id:

        flash(
            "You are not allowed to access this document.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        # ----------------------------------------
        # LOAD PDF
        # ----------------------------------------

        pages = load_document(
            document
        )

        # ----------------------------------------
        # CREATE PAGE-AWARE CHUNKS
        # ----------------------------------------

        chunks = []

        for page in pages:

            page_chunks = split_text(
                page["text"]
            )

            for chunk in page_chunks:

                chunks.append(
                    {
                        "text": chunk,
                        "page": page["page"]
                    }
                )

        if not chunks:

            flash(
                "No readable text was found in this document.",
                "error"
            )

            return redirect(
                url_for(
                    "open_document",
                    document_id=document.id
                )
            )

        # ----------------------------------------
        # EMBED QUESTION
        # ----------------------------------------

        question_embedding = embedding_model.encode(
            question
        )

        # ----------------------------------------
        # EMBED DOCUMENT CHUNKS
        # ----------------------------------------

        chunk_texts = [
            chunk["text"]
            for chunk in chunks
        ]

        chunk_embeddings = embedding_model.encode(
            chunk_texts
        )

        # ----------------------------------------
        # CALCULATE SIMILARITY
        # ----------------------------------------

        scored_chunks = []

        for index, chunk in enumerate(chunks):

            score = cosine_similarity(
                question_embedding,
                chunk_embeddings[index]
            )

            scored_chunks.append(
                {
                    "text": chunk["text"],
                    "page": chunk["page"],
                    "score": float(score)
                }
            )

        # ----------------------------------------
        # SORT BY RELEVANCE
        # ----------------------------------------

        scored_chunks.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        # ----------------------------------------
        # SELECT TOP CHUNKS
        # ----------------------------------------

        top_chunks = scored_chunks[:3]

        # ----------------------------------------
        # BUILD DOCUMENT CONTEXT
        # ----------------------------------------

        context_parts = []

        for item in top_chunks:

            context_parts.append(
                f"[Page {item['page']}]\n"
                f"{item['text']}"
            )

        document_context = "\n\n".join(
            context_parts
        )

        # ----------------------------------------
        # BUILD CHAT CONTEXT
        # ----------------------------------------

        conversation_context = (
            build_conversation_context(
                document.id
            )
        )

        # ----------------------------------------
        # BUILD AI PROMPT
        # ----------------------------------------

        prompt = f"""
You are an AI assistant that answers questions
about a user's uploaded PDF document.

Use ONLY the information provided in the document context.

If the answer is not present in the document context,
clearly say that the information was not found in the document.

Do not invent facts.

Be concise, clear, and useful.

You may use previous conversation context to understand
follow-up questions, but your factual answer must come
from the document.

DOCUMENT CONTEXT:

{document_context}

PREVIOUS CONVERSATION:

{conversation_context}

CURRENT QUESTION:

{question}

Answer the current question.
"""

        # ----------------------------------------
        # CALL OLLAMA
        # ----------------------------------------

        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        answer = response[
            "message"
        ][
            "content"
        ]

        # ----------------------------------------
        # CONVERT MARKDOWN
        # ----------------------------------------

        answer_html = markdown.markdown(
            answer
        )

        # ----------------------------------------
        # SAVE CHAT HISTORY
        # ----------------------------------------

        chat = ChatHistory(
            document_id=document.id,
            question=question,
            answer=answer
        )

        db.session.add(
            chat
        )

        db.session.commit()

        # ----------------------------------------
        # SOURCE PAGES
        # ----------------------------------------

        source_pages = sorted(
            set(
                item["page"]
                for item in top_chunks
            )
        )

        # ----------------------------------------
        # RENDER DASHBOARD
        # ----------------------------------------

        documents = Document.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Document.upload_date.desc()
        ).all()

        history = get_chat_history(
            document.id
        )

        return render_template(
            "index.html",
            documents=documents,
            current_document=document,
            answer=answer_html,
            question=question,
            source_pages=source_pages,
            chat_history=history
        )

    except Exception as error:

        print(
            "AI question error:",
            error
        )

        flash(
            "Something went wrong while processing your question.",
            "error"
        )

        return redirect(
            url_for(
                "open_document",
                document_id=document.id
            )
        )


# ============================================================
# SUMMARIZE DOCUMENT
# ============================================================

@app.route(
    "/summarize",
    methods=["POST"]
)
@login_required
def summarize():

    document_id = request.form.get(
        "document_id"
    )

    if not document_id:

        flash(
            "Please select a document first.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    document = Document.query.get_or_404(
        int(document_id)
    )

    # --------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------

    if document.user_id != current_user.id:

        flash(
            "You are not allowed to access this document.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        # ----------------------------------------
        # LOAD PDF
        # ----------------------------------------

        pages = load_document(
            document
        )

        full_text = "\n\n".join(
            page["text"]
            for page in pages
        )

        if not full_text.strip():

            flash(
                "No readable text was found in this document.",
                "error"
            )

            return redirect(
                url_for(
                    "open_document",
                    document_id=document.id
                )
            )

        # ----------------------------------------
        # LIMIT TEXT FOR LOCAL MODEL
        # ----------------------------------------

        summary_text = full_text[:12000]

        # ----------------------------------------
        # SUMMARY PROMPT
        # ----------------------------------------

        prompt = f"""
Create a clear and useful summary of the uploaded document.

Use only the information contained in the document.

Important rules:

- Do not invent information.
- Preserve numerical values accurately.
- Do not confuse CGPA with percentage.
- Keep important education, skills, projects,
  experience, achievements, and other relevant facts.
- Do not unnecessarily include private contact details.
- Use headings and bullet points where useful.
- Keep the summary reasonably concise.

DOCUMENT:

{summary_text}

SUMMARY:
"""

        # ----------------------------------------
        # CALL OLLAMA
        # ----------------------------------------

        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        summary = response[
            "message"
        ][
            "content"
        ]

        summary_html = markdown.markdown(
            summary
        )

        # ----------------------------------------
        # LOAD DOCUMENT LIST
        # ----------------------------------------

        documents = Document.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Document.upload_date.desc()
        ).all()

        # ----------------------------------------
        # CHAT HISTORY
        # ----------------------------------------

        history = get_chat_history(
            document.id
        )

        return render_template(
            "index.html",
            documents=documents,
            current_document=document,
            summary=summary_html,
            chat_history=history
        )

    except Exception as error:

        print(
            "Summary error:",
            error
        )

        flash(
            "Something went wrong while creating the summary.",
            "error"
        )

        return redirect(
            url_for(
                "open_document",
                document_id=document.id
            )
        )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

with app.app_context():

    db.create_all()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )