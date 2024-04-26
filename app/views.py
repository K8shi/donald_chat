from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

from rest_framework.decorators import api_view, schema
from rest_framework.response import Response
from rest_framework import status

from .forms import (
    UserLoginForm,
    UserRegistrationForm,
    DatabaseUploadForm,
    UserAPIKeyForm,
    UploadedZipFileForm,
    ChangePhotoForm,
    PineconeApiKeyForm
)
from .models import UserAPIKey, UploadedZipFile, User
import os
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
import time

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from collections import deque
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.question_answering import load_qa_chain
from langchain import OpenAI as openai
from langchain_pinecone import PineconeVectorStore as PVS
import json
model_name = "text-embedding-ada-002"
def HomeViewset(request, *args, **kwargs):

    return render(request, "pages/login.html")

# Account Related Views
def user_login(request):
    if request.method == "POST":
        login_form = UserLoginForm(request, request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data["username"]
            password = login_form.cleaned_data["password"]
            # Attempt to sign user in
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("app:chatbot")
            else:
                return render(
                    request,
                    "pages/login.html",
                    {
                        "login_form": login_form,
                    },
                )
        else:
            return render(
                request,
                "pages/login.html",
                {
                    "login_form": login_form,
                },
            )
    else:
        return render(
            request,
            "pages/login.html",
            {
                "login_form": UserLoginForm(),
            },
        )
    
def user_register(request):
    if request.method == "POST":
        signup_form = UserRegistrationForm(request.POST)
        if signup_form.is_valid():
            user = signup_form.save()
            login(request, user)
            return redirect("app:chatbot")
        else:
            return render(
                request,
                "pages/register.html",
                {"register_form": UserRegistrationForm(request.POST)},
            )
    return render(
        request,
        "pages/register.html",
        {
            "register_form": UserRegistrationForm(),
        },
    )


def user_logout(request):
    logout(request)
    return redirect("app:user_login")


def chatbot(request):
    from app.models import (AllowedUser, )
    
    if not UserAPIKey.objects.filter(user=request.user).first():
        return redirect("app:set_api_key")

    user_api = UserAPIKey.objects.filter(user=request.user).first()
    if not user_api.pinecone_api_key or not user_api.pinecone_index_name:
        return redirect("app:pinecone_configuration")
        

    db_error = False
    if not AllowedUser.objects.filter(user=request.user).exists():
        db_error = True
        return redirect("app:upload_zip_file")


    return render(request, "pages/chatbot.html", {"db_error": db_error})


def change_photo(request):
    if request.method == 'POST':
        form = ChangePhotoForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user

            # Update profile photo if provided
            if form.cleaned_data['user_photo']:
                user.profile_photo = form.cleaned_data['user_photo']
            else:
                # If no new photo, use the existing one as initial data
                form.initial['user_photo'] = user.profile_photo

            # Update bot icon if provided
            if form.cleaned_data['bot_icon']:
                user.bot_icon = form.cleaned_data['bot_icon']
            else:
                # If no new icon, use the existing one as initial data
                form.initial['bot_icon'] = user.bot_icon

            user.save()

            return redirect('app:chatbot')  # Redirect to the chatbot page or any other page
    else:
        # Pre-fill the form with the current user data
        initial_data = {}
        
        if request.user.profile_photo:
            # If the user has a profile photo, use its URL as initial data
            initial_data['user_photo'] = request.user.profile_photo

        if request.user.bot_icon:
            # If the user has a bot icon, use it as initial data
            initial_data['bot_icon'] = request.user.bot_icon

        form = ChangePhotoForm(initial=initial_data)

    return render(request, 'pages/change_photo.html', {'form': form})




def error_page(request):
    return render(
        request,
        "pages/error_page.html",
    )

def check_progress(request):
    try:
        PROGRESS_CHOICES = (
        ('starting_text_processing', 'Starting Text Processing'),
        ('text_processing_complete', 'Text Processing Complete'),
        ('starting_embedding', 'Starting Embedding'),
        ('embedding_complete', 'Embedding Complete'),
        ('complete', 'complete'),
        ('error', 'error'),
        )

        # Create a dictionary mapping keys to values
        progress_mapping = {key: value for key, value in PROGRESS_CHOICES} 
        if request.method == "GET":  
            uploaded_zip_file = UploadedZipFile.objects.filter(
                user=request.user
            ).first()
           
            status = uploaded_zip_file.progress
            progress = progress_mapping.get(status)
            return JsonResponse({'progress': progress, "status":status})
        return JsonResponse({'error': 'Uploaded zip file does not exist'}, status=404)
    except UploadedZipFile.DoesNotExist:
        return JsonResponse({'error': 'Uploaded zip file does not exist'}, status=404)
 

def upload_zip_file(request):
    if request.method == "POST":
        zip_file_form = UploadedZipFileForm(request.POST, request.FILES)
        if zip_file_form.is_valid():
            existing_uploaded_zip_file = UploadedZipFile.objects.filter(
                user=request.user
            ).first()
            if existing_uploaded_zip_file:
                existing_uploaded_zip_file.uploaded_zip_file = (
                    zip_file_form.cleaned_data["uploaded_zip_file"]
                ) 
                existing_uploaded_zip_file.save() 
            else:
                uploaded_zip_file = zip_file_form.save(commit=False)
                uploaded_zip_file.user = request.user
                uploaded_zip_file.save()
                 
            return redirect("app:chatbot")
    else:
        zip_file_form = UploadedZipFileForm()
    return render(
        request, "pages/upload_zip_file.html", {"zip_file_form": zip_file_form}
    )


def set_api_key(request):
    if request.method == "POST":
        api_key_form = UserAPIKeyForm(request.POST)
        if api_key_form.is_valid():
            api_key = api_key_form.cleaned_data["api_key"]
            openai_client = OpenAI(api_key=api_key)
            openai_response = test_openai_key(openai_client)
            if openai_response is None:
                api_key_form.add_error(
                    None,
                    "Provided API key is invalid or is not active. Please provide valid api key.",
                )
                return render(
                    request,
                    "pages/set_api_key.html",
                    {"api_key_form": api_key_form},
                )
            UserAPIKey.objects.update_or_create(
                user=request.user, defaults={"api_key": api_key}
            )
            return redirect("app:pinecone_configuration")
        else:
            return render(
                request, "pages/set_api_key.html", {"api_key_form": api_key_form}
            )
    else:
        try:
            user_api_key = request.user.api_key.api_key
        except:
            user_api_key = None
        api_key_form = UserAPIKeyForm(initial={"api_key": user_api_key})

    return render(
        request, "pages/set_api_key.html", {"api_key_form": api_key_form}
    )



def pinecone_configuration(request):
    if request.method == "POST":
        api_key_form = PineconeApiKeyForm(request.POST)
        if api_key_form.is_valid():
            pinecone_api_key = api_key_form.cleaned_data.get("pinecone_api_key")
            pinecone_index_name = api_key_form.cleaned_data.get("pinecone_index_name")
            UserAPIKey.objects.update_or_create(
                user=request.user, defaults={"pinecone_api_key": pinecone_api_key, "pinecone_index_name": pinecone_index_name}
            )
            return redirect("app:chatbot")
        else:
            return render(
                request, "pages/pinecone_configuration.html", {"pinecone_key_form": api_key_form}
            )
    else:
        try:
            pinecone_api_key = request.user.api_key.pinecone_api_key
            pinecone_index_name = request.user.api_key.pinecone_index_name
        except:
            pinecone_api_key = None
            pinecone_index_name = None
        api_key_form = PineconeApiKeyForm(initial={"pinecone_api_key": pinecone_api_key, "pinecone_index_name": pinecone_index_name})

    return render(
        request, "pages/pinecone_configuration.html", {"pinecone_key_form": api_key_form}
    )


# def upload_database(request):
#     if request.method == "POST":
#         database_form = DatabaseUploadForm(request.POST, request.FILES)
#         if database_form.is_valid():
#             uploaded_file = request.FILES["chromadb"]
#             user = request.user

#             if user.chromadb:
#                 # Delete the old chromadb file if it exists
#                 user.chromadb.delete()

#             user.chromadb = uploaded_file
#             user.collection = database_form.cleaned_data["collection"]
#             user.save()
#             return redirect("app:chatbot")
#     else:  # GET request
#         form_data = (
#             {"chromadb": request.user.chromadb, "collection": request.user.collection}
#             if request.user.chromadb
#             else None
#         )
#         database_form = DatabaseUploadForm(initial=form_data)

#     return render(
#         request,
#         "pages/upload_database.html",
#         {
#             "database_form": database_form,
#             "chromadb_name": (
#                 os.path.basename(request.user.chromadb.name)
#                 if request.user.chromadb
#                 else None
#             ),
#         },
#     )




# API
@api_view(["POST"])
def send_message(request):
    data = {"response": None, "status": 403, "error": "Someting went wrong."}

    # # Create a JsonResponse object with the JSON data
    if request.method == "POST":
        received_data = request.data
        user_query = received_data["user_query"]

        # """
        # Actual Issue
        #  - while in the process of creating chromadb using langchain they have not used any namespace but in the code provided it is referencing the namespace
        #  - In order to be compatible with langchain created chromdb I tried to replicate the same using langchain
        # """

        try:
            model_name = "text-embedding-ada-002"
            os.environ["PINECONE_API_KEY"] = request.user.api_key.pinecone_api_key
            llm = openai(model_name=model_name, temperature=.5, openai_api_key=request.user.api_key.api_key)
            embeddings = OpenAIEmbeddings(openai_api_key=request.user.api_key.api_key)
            index = PVS(index_name=request.user.api_key.pinecone_index_name, embedding=embeddings)
            docs = index.similarity_search(user_query.lower(), 3)

            query_respond = " ".join(doc.page_content for doc in docs)
            if query_respond:
                openai_client = OpenAI(api_key=request.user.api_key.api_key)
                chain = ChatOpenAI(openai_api_key=request.user.api_key.api_key)
                bot_response = ask_langchain(user_query, query_respond, chain)

                data["response"] = bot_response
                data["status"] = 200
                data["error"] = None

        except Exception as ex:
            raise ex
            pass  # Already handled
    return Response(data)


def ask_openai(user_query, query_respond, openai_client):
    system_message = f"""
    Answer the query based 
    on the provided information.
    INFORMATION
    ####
    {query_respond}
    ####   
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_query},
    ]

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.3
    )
    response_message = response.choices[0].message.content
    return response_message


history = deque(maxlen=100)


def ask_langchain(question, query_respond, chain: ChatOpenAI):
    """
    Asks a question using Langchain with conversation history tracking.

    Args:
        question: The user's question.
        api_key: Your OpenAI API key.
        history_size: Optional, the maximum number of past interactions to store (default: 10).

    Returns:
        The generated response without the "LLM:" prefix.
    """

    # Create the ChatOpenAI object

    # Define the prompt template
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"Answer the user's questions based on the context: {query_respond}",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )

    # Format the context string
    context_string = "\n".join(history)

    # Fill the template with context and question
    prompt = prompt_template.format(
        context=context_string, input=question, chat_history=list(history)
    )

    # Invoke the LLM with the filled prompt
    base_message = chain.invoke(prompt)

    # Update history after each call, removing "LLM:" prefix
    history.append(question + "\n" + base_message.content)
    # Return the response without "LLM:" prefix
    return base_message.content  # .split(':', 1)[1]


def test_openai_key(openai_client):
    user_query = "PING"

    system_message = f"""
    User will send Ping your task is to respond with PONG
    NO PREAMBLE and NO POSTAMBLE
    ####
    {user_query}
    ####
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_query},
    ]
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=messages, temperature=0.7
        )
        response_message = response.choices[0].message.content
        return response_message
    except:
        return None

def set_to_default_photo(request, *args, **kwargs):
    if request.method == "GET":
        user_id = kwargs.get("id")
        print("User ID:", user_id)
        if request.user.id == kwargs.get("id"):
            user =  request.user
            user.profile_photo = ""
            user.save()
            return redirect("/")
        
        
def set_to_default_icon(request, *args, **kwargs):
    if request.method == "GET":
        user_id = kwargs.get("id")
        if request.user.id == kwargs.get("id"):
            user =  request.user
            user.bot_icon = ""
            user.save()
            return redirect("/")
        
