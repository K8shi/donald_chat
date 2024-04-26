"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.auth.decorators import login_required
from django.urls import path
from . import views
from .custom_decorator import anonymous_required


app_name = 'app'
urlpatterns = [
    # Primary Views
    path("", login_required(views.chatbot), name="chatbot"),
    # path("upload_database/", login_required(views.upload_database), name="upload_database"),
    path("upload_zip_file/", login_required(views.upload_zip_file), name="upload_zip_file"),
    path("error_page/", views.error_page, name="error_page"),
    path("set-api-key/", login_required(views.set_api_key), name="set_api_key"),
    path("pinecone-configuration/", login_required(views.pinecone_configuration), name="pinecone_configuration"),
    
    # Account Related Views
    path("login/", anonymous_required(views.user_login), name="user_login"),
    path("logout/", login_required(views.user_logout), name="user_logout"),
    path("register/", anonymous_required(views.user_register), name="user_register"),
    path("remove/profile/<int:id>/photo", login_required(views.set_to_default_photo), name="set_to_default_photo"),
    path("remove/profile/<int:id>/icon", login_required(views.set_to_default_icon), name="set_to_default_icon"),
    path('change_photo/', login_required(views.change_photo), name='change_photo'),

    # API
    path("api/send-message/", login_required(views.send_message), name="send_message"),
    path("api/check_progress/", login_required(views.check_progress), name="check_progress"),
    
]
