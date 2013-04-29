from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.forms.models import modelform_factory

def view_profile(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'registration/profile.html', {'user': user})

def edit_user(request, username=None):
    if username:
        user = get_object_or_404(User, username=username)
        if user != request.user:
            return HttpResponseForbidden()
    else:
        user = User()
        
    user_form = modelform_factory(User)
    if request.method == "POST":
        form = user_form(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            # Do something. Should generally end with a redirect. For example:
            return HttpResponseRedirect(user.get_absolute_url())
    else:
        form = user_form(instance=user)
        
    context = {"form": form}
    return render(request, "registration/edit_user.html", context)