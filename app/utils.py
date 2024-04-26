import os
import shutil
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.vectorstores import pinecone
from langchain_openai import OpenAIEmbeddings
from django.conf import settings
from pinecone import Pinecone, ServerlessSpec
from langchain.chains.question_answering import load_qa_chain
from langchain import OpenAI
from langchain_pinecone import PineconeVectorStore as PVS
env = os.environ


def remove_files_and_folders(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def ensure_directory_exists(directory):
    """Ensures that the specified directory exists."""
    os.makedirs(directory, exist_ok=True)


def write_to_temp_file(document_name_path, content):
    """Writes content to a text file in the temp directory."""
    with open(
        document_name_path, "w", encoding="utf-8"
    ) as text_file:  # Specify UTF-8 encoding here
        text_file.write(content)


def process_document(user, file_path, loader_class, final_doc_path):
    """Processes a document and writes its content to a temp file."""
    print(f"Processing file: {file_path}") 
    loader = loader_class(file_path)  
    documents = loader.load()  
    combined_page_contents = "\n\n".join(doc.page_content for doc in documents)
    document_name = os.path.splitext(os.path.basename(file_path))[0]
    document_name_path = f"{final_doc_path}/{document_name}.txt"
    write_to_temp_file(document_name_path, combined_page_contents)
    return {document_name: combined_page_contents}

         
def process_files(user, folder_path, final_doc_path):
    """Processes all DOCX and PDF files in the given folder path."""
    all_processed_files = [] 
    for root, _, files in os.walk(folder_path):
        if "__MACOSX" not in root and "processed" not in root:
            for file in files:
                file_path = os.path.normpath(os.path.join(root, file))
                file_extension = file.lower()
                if file_extension.endswith(".docx"):
                    result = process_document(user, file_path, Docx2txtLoader, final_doc_path)
                    if result:
                        all_processed_files.append(result)
                elif file_extension.endswith(".pdf"):
                    result = process_document(user, file_path, PyPDFLoader, final_doc_path)
                    if result:
                        all_processed_files.append(result)  
    return all_processed_files



def load_and_split_documents(file_path, chunk_size, chunk_overlap):
    """Loads documents from a directory and splits them into chunks."""
    text_loader_kwargs={'autodetect_encoding': True}
    loader = DirectoryLoader(
        file_path,
        glob="**/*.txt",
        loader_cls=TextLoader,
        show_progress=True,
        loader_kwargs=text_loader_kwargs,
        use_multithreading=False,
        max_concurrency=1
    )
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return text_splitter.split_documents(documents)


def create_embeddings(user, model_name):
    """Creates an embeddings object based on the model name."""
    return OpenAIEmbeddings(
        openai_api_key=user.api_key.api_key,
        model=model_name
    )


def create_or_load_vector_db(user, docs, embeddings, persist_directory):
    """Creates or loads a vector database from documents and embeddings."""
    import os
    os.environ["PINECONE_API_KEY"] = user.api_key.pinecone_api_key
    PVS.from_documents(docs, embeddings, index_name=user.api_key.pinecone_index_name)
    # pinecone.from_texts([t.page_content for t in docs], embeddings, index_name="donald")



def make_chroma_db(user, documents_path, chroma_db_path, zip_file, extract_path):
    from app.models import AllowedUser
    final_doc_path = f"{documents_path}/processed"
    ensure_directory_exists(final_doc_path)
    all_processed_files = process_files(user, documents_path, final_doc_path)
    zip_file.progress = "text_processing_complete" 
    zip_file.save_field()
    if len(all_processed_files) > 0:
        zip_file.progress = "starting_embedding" 
        zip_file.save_field()
        docs = load_and_split_documents(final_doc_path, chunk_size=750, chunk_overlap=100)
        embeddings = create_embeddings(user, "text-embedding-ada-002")
        vectordb = create_or_load_vector_db(user, docs, embeddings, chroma_db_path)

        zip_file.progress = "embedding_complete" 
        zip_file.save_field()
        if not AllowedUser.objects.filter(user=user).exists():
            AllowedUser.objects.create(user=user)
    else:
        try:
            os.remove(f"{chroma_db_path}/chroma.sqlite3")
        except:
            pass
    remove_files_and_folders(documents_path)
    zip_file.progress = "complete" 
    zip_file.save_field()
