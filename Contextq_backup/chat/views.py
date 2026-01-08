# chat/views.py
import uuid
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import UploadedFile, ChatMessage, ChatSession
from documents.forms import UploadFileForm, AskQuestionForm
from documents.utils import extract_text, preprocess_text, store_chunks_with_embeddings, get_answer_with_sources
from django.core.files.storage import FileSystemStorage


@login_required
def index(request):
    uploaded_files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    selected_file = None
    chat_history = []

    if 'file_id' in request.GET:
        selected_file = get_object_or_404(UploadedFile, id=request.GET['file_id'], user=request.user)
        chat_history = ChatMessage.objects.filter(file=selected_file).order_by('timestamp')

    upload_form = UploadFileForm()
    ask_form = AskQuestionForm()

    return render(request, 'home/index.html', {
        'uploaded_files': uploaded_files,
        'selected_file': selected_file,
        'chat_history': chat_history,
        'upload_form': upload_form,
        'ask_form': ask_form,
        "chat_sessions": ChatSession.objects.filter(user=request.user).order_by("-created_at")

    })


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.cleaned_data['file']
            instance = UploadedFile.objects.create(user=request.user, file=file_obj)

            text = extract_text(file_obj, file_obj.name)
            clean_text = preprocess_text(text)

            store_chunks_with_embeddings(clean_text, file_obj.name)

            messages.success(request, "File uploaded and indexed.")
            return redirect("chat:index")
    return redirect('chat:index')


@login_required
def ask_question(request, chat_id):
    if request.method == "POST":
        query = request.POST.get("query")

        if not query.strip():
            return redirect("chat:chat_view", chat_id=chat_id)

        chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)

        answer, sources = get_answer_with_sources(query, chat_id)

        ChatMessage.objects.create(
            chat=chat,
            user=request.user,
            question=query,
            answer=answer,
        )

        return redirect("chat:chat_view", chat_id=chat_id)

    return redirect("chat:index")


@login_required
def start_chat(request):
    if request.method == "POST":
        uploaded_file = request.FILES["file"]
        file_name = uploaded_file.name

        fs = FileSystemStorage()
        fs.save(file_name, uploaded_file)

        text = extract_text(uploaded_file, file_name)
        chat_id = str(uuid.uuid4())  # ✅ Needs to be a string for Chroma

        print(f"[INFO] Using chat_id: {chat_id}")

        store_chunks_with_embeddings(text, file_name, namespace=chat_id)

        # ✅ Make sure session is saved
        chat = ChatSession.objects.create(
            id=chat_id,
            user=request.user,
            file_name=file_name,
        )

        print("[SUCCESS] ChatSession created:", chat)

        return redirect("chat:chat_view", chat_id=chat.id)

    return redirect("chat:index")


@login_required
def chat_view(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
    messages = ChatMessage.objects.filter(chat=chat).order_by("created_at")
    all_sessions = ChatSession.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "home/index.html", {
        "file_name": chat.file_name,
        "conversation": messages,
        "current_chat_id": chat.id,
        "chat_sessions": all_sessions
    })


@require_POST
@login_required
def delete_session(request, chat_id):
    session = get_object_or_404(ChatSession, id=chat_id, user=request.user)
    session.delete()
    messages.success(request, "Session deleted.")
    return redirect("chat:index")