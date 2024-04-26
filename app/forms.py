from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, validate_file_size, UserAPIKey, UploadedZipFile

class ChangePhotoForm(forms.Form):
    user_photo = forms.ImageField(label='Select a new profile photo', required=False)
    bot_icon = forms.ImageField(label='Select a new bot icon', required=False)

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "p-2",
                "placeholder": "Joe",
                "autofocus": True,
                "autocapitalize": "none",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "p-2 input-field",
                "placeholder": "Password",
            }
        ),
    )


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "p-2",
                "placeholder": "Email",
                "autofocus": True,
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "p-2",
                    "placeholder": "Username",
                    "autofocus": True,
                    "autocapitalize": "none",
                    "autocomplete": "username",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs["placeholder"] = "Password"
        self.fields["password1"].widget.attrs["class"] = "p-2"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirm Password"
        self.fields["password2"].widget.attrs["class"] = "p-2"


class DatabaseUploadForm(forms.Form):
    collection = forms.CharField(
        max_length=63,
        min_length=3,
        widget=forms.TextInput(
            attrs={
                "class": "col-9 p-2",
                "placeholder": "my_collection",
                "autofocus": True,
            }
        ),
    )
    chromadb = forms.FileField(
        validators=[
            FileExtensionValidator(allowed_extensions=["sqlite3"]),
            validate_file_size,
        ]
    )


def validate_api_key(value):
    if not value.startswith('sk-'):
        raise ValidationError('API key must start with "sk-"')


class UserAPIKeyForm(forms.Form):
    api_key = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "p-2 input-field form-control",
                "placeholder": "API Key starting with sk-"
            }
        ),
        validators=[validate_api_key]
    )

class PineconeApiKeyForm(forms.Form):
    pinecone_api_key = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "p-2 input-field form-control",
                "placeholder": "Pinecone API Key"
            }
        ),
    )
    pinecone_index_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "p-2 input-field form-control",
                "placeholder": "Pinecone Index Name"
            }
        ),
    )

    

class UploadedZipFileForm(forms.ModelForm):
    class Meta:
        model = UploadedZipFile
        fields = ['uploaded_zip_file']
