from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

def view_profile(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'registration/profile.html', {'user': user})