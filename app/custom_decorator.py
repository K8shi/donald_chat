from django.shortcuts import redirect
from . import views 

def anonymous_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)  # Allow access to non-logged-in or admin users
        else:
            # Redirect authenticated users to another page
            return redirect('app:chatbot') 

    return _wrapped_view
