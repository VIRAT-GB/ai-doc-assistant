import os
import re
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

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
import markdown

from models import db, User, Document, ChatHistory


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "ai-doc-assistant-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///documents.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# UPLOAD CONFIGURATION
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
# DATABASE
# ============================================================

db.init_app(app)


# ============================================================
# LOGIN MANAGER
# ============================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# ============================================================
# PDF PROCESSING
# ============================================================

def load_document(document):

    filename = (
        document.stored_filename
        or document.filename
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    if not os.path.exists(file_path):

        return []

    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        text = page.extract_text() or ""

        text = text.strip()

        if text:

            pages.append(
                {
                    "page": page_number,
                    "text": text
                }
            )

    return pages


# ============================================================
# SIMPLE TEXT CHUNKING
# ============================================================

def split_text(text, chunk_size=1000):

    words = text.split()

    chunks = []

    current_chunk = []

    current_length = 0

    for word in words:

        current_chunk.append(word)

        current_length += len(word) + 1

        if current_length >= chunk_size:

            chunks.append(
                " ".join(current_chunk)
            )

            current_chunk = []

            current_length = 0

    if current_chunk:

        chunks.append(
            " ".join(current_chunk)
        )

    return chunks


# ============================================================
# KEYWORD SEARCH
#
# Lightweight replacement for the heavy embedding model
# used by the local development version.
# ============================================================

def search_document(pages, question, limit=3):

    question_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            question.lower()
        )
    )

    stop_words = {
        "what",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "my",
        "me",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "from",
        "about",
        "tell",
        "give",
        "show",
        "does",
        "do",
        "how",
        "which",
        "who"
    }

    question_words = (
        question_words - stop_words
    )

    scored_pages = []

    for page in pages:

        text = page["text"]

        text_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                text.lower()
            )
        )

        score = len(
            question_words & text_words
        )

        if score > 0:

            scored_pages.append(
                {
                    "page": page["page"],
                    "text": text,
                    "score": score
                }
            )

    scored_pages.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return scored_pages[:limit]


# ============================================================
# EXTRACTIVE ANSWER
# ============================================================

def generate_answer(question, results):

    if not results:

        return (
            "I could not find information related "
            "to your question in this document."
        )

    question_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            question.lower()
        )
    )

    stop_words = {
        "what",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "my",
        "me",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "from",
        "about",
        "tell",
        "give",
        "show",
        "does",
        "do",
        "how",
        "which",
        "who"
    }

    question_words -= stop_words

    candidate_sentences = []

    for result in results:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            result["text"]
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:

                continue

            sentence_words = set(
                re.findall(
                    r"\b[a-zA-Z0-9]+\b",
                    sentence.lower()
                )
            )

            matches = len(
                question_words & sentence_words
            )

            if matches > 0:

                candidate_sentences.append(
                    (
                        matches,
                        sentence,
                        result["page"]
                    )
                )

    candidate_sentences.sort(
        key=lambda item: item[0],
        reverse=True
    )

    selected = []

    for _, sentence, page in candidate_sentences:

        if sentence not in selected:

            selected.append(sentence)

        if len(selected) >= 3:

            break

    if not selected:

        return results[0]["text"][:1000]

    return " ".join(selected)


# ============================================================
# CHAT HISTORY
# ============================================================

def get_chat_history(document_id):

    return (
        ChatHistory.query
        .filter_by(
            document_id=document_id
        )
        .order_by(
            ChatHistory.created_at.desc()
        )
        .limit(5)
        .all()
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = (
            request.form.get("username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        )

        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return render_template(
                "register.html"
            )

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Username already exists.",
                "error"
            )

            return render_template(
                "register.html"
            )

        user = User(
            username=username,
            password_hash=generate_password_hash(
                password
            )
        )

        db.session.add(user)

        db.session.commit()

        flash(
            "Registration successful. Please log in.",
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

    if request.method == "POST":

        username = (
            request.form.get("username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if (
            user
            and check_password_hash(
                user.password_hash,
                password
            )
        ):

            login_user(user)

            flash(
                "Welcome back!",
                "success"
            )

            return redirect(
                url_for("index")
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
# HOME / DASHBOARD
# ============================================================

@app.route("/")
@login_required
def index():

    documents = (
        Document.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Document.upload_date.desc()
        )
        .all()
    )

    selected_document = None

    document_id = request.args.get(
        "document_id",
        type=int
    )

    if document_id:

        selected_document = (
            Document.query
            .filter_by(
                id=document_id,
                user_id=current_user.id
            )
            .first()
        )

    if (
        not selected_document
        and documents
    ):

        selected_document = documents[0]

    chat_history = []

    if selected_document:

        chat_history = get_chat_history(
            selected_document.id
        )

    return render_template(
        "index.html",
        documents=documents,
        current_document=selected_document,
        chat_history=chat_history
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

    if "file" not in request.files:

        flash(
            "No file selected.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    file = request.files["file"]

    if not file.filename:

        flash(
            "Please select a PDF file.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    if not allowed_file(file.filename):

        flash(
            "Only PDF files are allowed.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    original_filename = secure_filename(
        file.filename
    )

    file_extension = os.path.splitext(
        original_filename
    )[1].lower()

    unique_filename = (
        f"{uuid.uuid4().hex}"
        f"{file_extension}"
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    try:

        file.save(file_path)

        document = Document(
            filename=original_filename,
            stored_filename=unique_filename,
            user_id=current_user.id
        )

        db.session.add(document)

        db.session.flush()

        pages = load_document(document)

        full_text = "\n".join(
            page["text"]
            for page in pages
        )

        chunks = split_text(
            full_text
        )

        document.chunk_count = len(chunks)

        db.session.commit()

        flash(
            "PDF uploaded successfully.",
            "success"
        )

        return redirect(
            url_for(
                "index",
                document_id=document.id
            )
        )

    except Exception as error:

        db.session.rollback()

        if os.path.exists(file_path):

            os.remove(file_path)

        flash(
            f"Upload failed: {error}",
            "error"
        )

        return redirect(
            url_for("index")
        )


# ============================================================
# OPEN DOCUMENT
# ============================================================

@app.route(
    "/open/<int:document_id>"
)
@login_required
def open_document(document_id):

    document = (
        Document.query
        .filter_by(
            id=document_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    return redirect(
        url_for(
            "index",
            document_id=document.id
        )
    )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.route(
    "/delete/<int:document_id>"
)
@login_required
def delete_document(document_id):

    document = (
        Document.query
        .filter_by(
            id=document_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    filename = (
        document.stored_filename
        or document.filename
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    try:

        if os.path.exists(file_path):

            os.remove(file_path)

        ChatHistory.query.filter_by(
            document_id=document.id
        ).delete()

        db.session.delete(document)

        db.session.commit()

        flash(
            "Document deleted successfully.",
            "success"
        )

    except Exception as error:

        db.session.rollback()

        flash(
            f"Could not delete document: {error}",
            "error"
        )

    return redirect(
        url_for("index")
    )


# ============================================================
# ASK QUESTION
# ============================================================

@app.route(
    "/ask",
    methods=["POST"]
)
@login_required
def ask():

    document_id = request.form.get(
        "document_id",
        type=int
    )

    question = (
        request.form.get("question")
        or ""
    ).strip()

    if not document_id:

        flash(
            "Please select a document.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    document = (
        Document.query
        .filter_by(
            id=document_id,
            user_id=current_user.id
        )
        .first()
    )

    if not document:

        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    if not question:

        flash(
            "Please enter a question.",
            "error"
        )

        return redirect(
            url_for(
                "index",
                document_id=document.id
            )
        )

    pages = load_document(document)

    results = search_document(
        pages,
        question
    )

    answer = generate_answer(
        question,
        results
    )

    source_pages = sorted(
        set(
            result["page"]
            for result in results
        )
    )

    answer_html = markdown.markdown(
        answer
    )

    history = ChatHistory(
        document_id=document.id,
        question=question,
        answer=answer
    )

    db.session.add(history)

    db.session.commit()

    chat_history = get_chat_history(
        document.id
    )

    return render_template(
        "index.html",
        documents=(
            Document.query
            .filter_by(
                user_id=current_user.id
            )
            .order_by(
                Document.upload_date.desc()
            )
            .all()
        ),
        current_document=document,
        answer=answer_html,
        source_pages=source_pages,
        question=question,
        chat_history=chat_history
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
        "document_id",
        type=int
    )

    document = (
        Document.query
        .filter_by(
            id=document_id,
            user_id=current_user.id
        )
        .first()
    )

    if not document:

        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    pages = load_document(document)

    full_text = "\n".join(
        page["text"]
        for page in pages
    )

    if not full_text.strip():

        flash(
            "No readable text was found in this PDF.",
            "error"
        )

        return redirect(
            url_for(
                "index",
                document_id=document.id
            )
        )

    sentences = re.split(
        r"(?<=[.!?])\s+",
        full_text
    )

    summary_sentences = []

    for sentence in sentences:

        sentence = sentence.strip()

        if sentence:

            summary_sentences.append(
                sentence
            )

        if len(summary_sentences) >= 8:

            break

    summary = " ".join(
        summary_sentences
    )

    summary_html = markdown.markdown(
        summary
    )

    return render_template(
        "index.html",
        documents=(
            Document.query
            .filter_by(
                user_id=current_user.id
            )
            .order_by(
                Document.upload_date.desc()
            )
            .all()
        ),
        current_document=document,
        summary=summary_html,
        chat_history=get_chat_history(
            document.id
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