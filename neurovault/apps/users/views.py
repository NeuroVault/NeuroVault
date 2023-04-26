import datetime
from django.conf import settings

from django.http.response import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.template.context import RequestContext
from django.urls import reverse, reverse_lazy
from django.utils.crypto import get_random_string
from django.views.generic import View, CreateView, UpdateView, DeleteView, ListView


from braces.views import LoginRequiredMixin
from oauth2_provider.views.application import ApplicationOwnerIsUserMixin
from oauth2_provider.models import RefreshToken, AccessToken, Application
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .forms import UserEditForm, UserCreateForm, ApplicationEditForm


def view_profile(request, username=None):
    if not username:
        if not request.user:
            return HttpResponseForbidden()
        else:
            user = request.user
    else:
        user = get_object_or_404(User, username=username)
    return render(request, "registration/profile.html", {"user": user})


def create_user(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES, instance=User())
        if form.is_valid():
            form.save()
            new_user = authenticate(
                username=request.POST["username"], password=request.POST["password1"]
            )
            login(request, new_user)
            # Do something. Should generally end with a redirect. For example:
            if request.POST["next"]:
                return HttpResponseRedirect(request.POST["next"])
            else:
                return HttpResponseRedirect(reverse("statmaps:my_collections"))
    else:
        form = UserCreateForm(instance=User())

    context = {"form": form, "request": request}
    return render(request, "registration/edit_user.html", context)


@login_required
def edit_user(request):
    edit_form = UserEditForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        if edit_form.is_valid():
            edit_form.save()
            messages.success(request, "Your profile has been successfully updated.")

            return HttpResponseRedirect(reverse("users:edit_user"))
    return render(request, "registration/edit_profile.html", {"form": edit_form})


@login_required
def delete_profile(request):
    if request.GET.get("delete-btn"):
        if request.user.username == (request.GET.get("delete-text")):
            request.user.delete()
        else:
            messages.warning(request, "Username did not match, deletion not completed")
        return HttpResponseRedirect(reverse("users:delete_profile"))
    return render(request, "registration/delete_profile.html")


@login_required
def password_change_done(request):
    messages.success(request, "Your password has been successfully updated.")

    return HttpResponseRedirect(reverse("users:password_change"))

@login_required
def view_token(request, regenerate=False):
    if regenerate:
        try:
            old_token = Token.objects.get(user=request.user)
            old_token.delete()
        except Token.DoesNotExist:
            pass
        token = Token.objects.create(user=request.user)
    else:
        token, _ = Token.objects.get_or_create(user=request.user)
    return render(request, 'show_token.html', {'token': token.key})
