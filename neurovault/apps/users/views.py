from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, render_to_response
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth import authenticate, login
from .forms import UserEditForm, UserCreateForm, ApplicationEditForm
from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext
from oauth2_provider.views.application import ApplicationOwnerIsUserMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from braces.views import LoginRequiredMixin
from django.utils.html import escape


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
    return render_to_response("registration/edit_profile.html",
                              {'form': edit_form},
                              context_instance=RequestContext(request))

# def login(request):
#     return render_to_response('home.html', {
#         'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None)
#     }, RequestContext(request))


class ApplicationRegistration(LoginRequiredMixin, CreateView):
    """
    View used to register a new Application for the request.user
    """
    form_class = ApplicationEditForm
    template_name = "oauth2_provider/application_registration_form.html"

    def get_success_url(self):
        return reverse('developerapps_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request,
                         'The application has been successfully registered.')

        return super(ApplicationRegistration, self).form_valid(form)


class ApplicationUpdate(ApplicationOwnerIsUserMixin, UpdateView):
    """
    View used to update an application owned by the request.user
    """
    context_object_name = 'application'
    form_class = ApplicationEditForm
    template_name = 'oauth2_provider/application_form.html'

    def get_success_url(self):
        return reverse('developerapps_list')

    def form_valid(self, form):
        messages.success(self.request,
                         'The application has been successfully updated.')
        return super(ApplicationUpdate, self).form_valid(form)


class ApplicationDelete(ApplicationOwnerIsUserMixin, DeleteView):
    """
    View used to delete an application owned by the request.user
    """
    context_object_name = 'application'
    success_url = reverse_lazy('developerapps_list')
    template_name = "oauth2_provider/application_confirm_delete.html"
    success_message = 'The application has been successfully deleted.'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(ApplicationDelete, self).delete(request, *args, **kwargs)
