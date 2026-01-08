from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from documents.models import ChatHistory
from documents.utils import extract_text, split_text_into_chunks, store_chunks_with_embeddings, get_answer_with_sources



@login_required
def index(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        file_path = save_uploaded_file(uploaded_file)
        text = extract_text(uploaded_file, file_name)
        text_chunks = split_text_into_chunks(text)  # ✅ apply proper chunking here
        store_chunks_with_embeddings(text_chunks, file_name)

        messages.success(request, "File uploaded and indexed!")
        return redirect('/')
    return render(request, 'home/index.html')


def save_uploaded_file(file):
    fs = FileSystemStorage()
    filename = fs.save(file.name, file)
    return fs.url(filename)

