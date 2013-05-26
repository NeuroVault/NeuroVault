from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, render_to_response
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login
from .forms import UserEditForm, UserCreateForm
from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext

def view_profile(request, username=None):
    if not username:
        if not request.user:
            return HttpResponseForbidden()
        else:
            user = request.user
    else:
        user = get_object_or_404(User, username=username)
    return render(request, 'registration/profile.html', {'user': user})

def create_user(request):

    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES, instance=User())
        if form.is_valid():
            form.save()
            new_user = authenticate(username=request.POST['username'],
                                    password=request.POST['password1'])
            login(request, new_user)
            # Do something. Should generally end with a redirect. For example:
            if request.POST['next']:
                return HttpResponseRedirect(request.POST['next'])
            else:
                return HttpResponseRedirect(reverse("my_profile"))
    else:
        form = UserCreateForm(instance=User())
        
    context = {"form": form,
               "request": request}
    return render(request, "registration/edit_user.html", context)

@login_required
def edit_user(request):
    edit_form = UserEditForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        if edit_form.is_valid():
            edit_form.save()
            return HttpResponseRedirect(reverse("my_profile"))
    return render_to_response("registration/edit_user.html",
                             {'form':edit_form},
                             context_instance=RequestContext(request))
