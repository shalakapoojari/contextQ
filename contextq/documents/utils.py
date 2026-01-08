import os
import pdfplumber
from docx import Document
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from langchain_community.llms.ollama import Ollama
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_community.vectorstores import Chroma
from langchain_community.llms import LlamaCpp
from langchain.text_splitter import RecursiveCharacterTextSplitter

CHROMA_DIR = "chroma_db"
LLM_MODEL_PATH = "models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

# -----------------------------
# Embedding Wrapper
# -----------------------------
class ChromaCompatibleEmbeddingFunction:
    def __init__(self, model_name="intfloat/multilingual-e5-base"):
        self._embedder = HuggingFaceEmbeddings(model_name=model_name)

    def __call__(self, input):
        return self._embedder.embed_documents(input)

    def embed_documents(self, texts):
        return self._embedder.embed_documents(texts)

    def embed_query(self, text):
        return self._embedder.embed_query(text)

    def name(self):
        return "huggingface-compatible"

# -----------------------------
# Text Extraction
# -----------------------------
def extract_text_from_pdf(file_obj):
    with pdfplumber.open(file_obj) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)

def extract_text_from_txt(file_obj):
    file_obj.seek(0)
    return file_obj.read().decode("utf-8")

def extract_text_from_docx(file_obj):
    file_obj.seek(0)
    doc = Document(file_obj)
    paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)

def extract_text(file_obj, file_name):
    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(file_obj)
    elif file_name.endswith(".txt"):
        return extract_text_from_txt(file_obj)
    elif file_name.endswith(".docx"):
        return extract_text_from_docx(file_obj)
    else:
        return "Unsupported file type"

# -----------------------------
# Preprocessing
# -----------------------------
def preprocess_text(raw_text):
    lines = raw_text.splitlines()
    buffer, current = [], ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        current += " " + line
        if len(current) > 80:
            buffer.append(current.strip())
            current = ""
    if current:
        buffer.append(current.strip())
    print(f"[INFO] Preprocessed into {len(buffer)} blocks")
    return "\n".join(buffer)

# -----------------------------
# Chunking
# -----------------------------
def split_text_into_chunks(text, chunk_size=800, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    chunks = splitter.split_text(text)
    cleaned_chunks = []

    seen = set()
    for chunk in chunks:
        c = chunk.strip()
        if len(c) < 30 or c.lower() in seen:
            continue
        cleaned_chunks.append(c)
        seen.add(c.lower())

    print(f"[INFO] Final cleaned chunks: {len(cleaned_chunks)}")
    return cleaned_chunks

# -----------------------------
# Vector Store
# -----------------------------
def get_chroma_collection(namespace):
    embeddings = ChromaCompatibleEmbeddingFunction("intfloat/multilingual-e5-base")
    return Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=namespace
    )

def store_chunks_with_embeddings(raw_text, file_name, namespace):
    preprocessed = preprocess_text(raw_text)
    chunks = split_text_into_chunks(preprocessed)

    if not chunks:
        print(f"[ERROR] No valid chunks extracted from {file_name}")
        return

    vectorstore = get_chroma_collection(namespace)
    metadatas = [{"source": file_name} for _ in chunks]

    print(f"[INFO] Storing {len(chunks)} cleaned chunks for: {file_name} in namespace: {namespace}")
    vectorstore.add_texts(chunks, metadatas=metadatas)
    vectorstore.persist()

# -----------------------------
# Local Mistral LLM
# -----------------------------
def get_local_llm():
    return Ollama(
        model="mistral",
        base_url="http://localhost:11434",  # default Ollama endpoint
        temperature=0.1,
        top_p=0.95,
        stop=["</s>"],
        num_ctx=2048
    )

# -----------------------------
# Prompt + Answer Retrieval
# -----------------------------
QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a document-based question answering system.

Rules:
- Use ONLY the information from the context.
- Do NOT use outside knowledge.
- If the answer is not explicitly stated, reply exactly:
  "Answer not found in the document."

Context:
{context}

Question:
{question}

Answer:
"""
)


def get_answer_with_sources(query, namespace):
    if not query.strip():
        raise ValueError("Query cannot be empty")
    
    namespace_str = str(namespace)
    vectorstore = get_chroma_collection(namespace_str)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)

    context = "\n\n".join([doc.page_content for doc in docs])
    print(f"[DEBUG] Context Preview: {context[:300]}...")

    llm = get_local_llm()
    chain = QA_PROMPT | llm
    result = chain.invoke({"context": context, "question": query})
    
    return result.strip(), [doc.metadata for doc in docs]