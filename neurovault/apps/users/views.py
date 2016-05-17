import datetime
from django.conf import settings

from django.http.response import (HttpResponseRedirect, HttpResponseForbidden,
                                  Http404)
from django.utils.crypto import get_random_string
from django.shortcuts import render, get_object_or_404, render_to_response
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth import authenticate, login
from .forms import UserEditForm, UserCreateForm, ApplicationEditForm
from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext
from oauth2_provider.views.application import ApplicationOwnerIsUserMixin
from oauth2_provider.models import RefreshToken, AccessToken, Application
from django.views.generic import (View, CreateView, UpdateView, DeleteView,
                                  ListView)
from braces.views import LoginRequiredMixin


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
                return HttpResponseRedirect(reverse("my_collections"))
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
            messages.success(request,
                             'Your profile has been successfully updated.')

            return HttpResponseRedirect(reverse("edit_user"))
    return render_to_response("registration/edit_profile.html",
                              {'form': edit_form},
                              context_instance=RequestContext(request))

@login_required
def delete_profile(request):
    if(request.GET.get('delete-btn')):
        if request.user.username == (request.GET.get('delete-text')):
            request.user.delete()
        else: messages.warning(request,'Username did not match, deletion not completed')
        return HttpResponseRedirect(reverse("delete_profile"))
    return render_to_response("registration/delete_profile.html",
                              context_instance=RequestContext(request))

@login_required
def password_change_done(request):
    messages.success(request,
                     'Your password has been successfully updated.')

    return HttpResponseRedirect(reverse("password_change"))


# def login(request):
#     return render_to_response('home.html', {
#         'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None)
#     }, RequestContext(request))


class PersonalTokenUserIsRequestUserMixin(LoginRequiredMixin):

    """
    This mixin is used to provide an Connection queryset filtered by the
    current request.user.
    """
    fields = '__all__'

    def get_queryset(self):
        return AccessToken.objects.filter(
            user=self.request.user,
            application_id=settings.DEFAULT_OAUTH_APPLICATION_ID
        )


class PersonalTokenList(PersonalTokenUserIsRequestUserMixin, ListView):
    model = AccessToken
    template_name = 'oauth2_provider/personal_token_list.html'


class PersonalTokenCreate(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        application = Application.objects.get(
            pk=settings.DEFAULT_OAUTH_APPLICATION_ID)
        AccessToken.objects.create(user=self.request.user,
                                   token=get_random_string(
                                       length=settings.OAUTH_PERSONAL_TOKEN_LENGTH),
                                   application=application,
                                   expires=datetime.date(datetime.MAXYEAR,
                                                         12, 30),
                                   scope='read write')
        messages.success(self.request,
                         'The new token has been successfully generated.')

        return HttpResponseRedirect(reverse('token_list'))


class PersonalTokenDelete(PersonalTokenUserIsRequestUserMixin, DeleteView):
    template_name = 'oauth2_provider/personal_token_confirm_delete.html'
    success_url = reverse_lazy('token_list')
    success_message = ('The token has been successfully deleted.')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.revoke()
        messages.success(self.request, self.success_message)

        return HttpResponseRedirect(success_url)


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
    template_name = 'oauth2_provider/application_form.html'

    # Reset the inherited fields attribute and use a form_class instead
    fields = None
    form_class = ApplicationEditForm

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
    template_name = 'oauth2_provider/application_confirm_delete.html'
    success_message = 'The application has been successfully deleted.'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(ApplicationDelete, self).delete(request, *args, **kwargs)


class ConnectionList(LoginRequiredMixin, ListView):
    template_name = 'oauth2_provider/connection_list.html'

    def get_queryset(self):
        return (RefreshToken.objects
                .filter(user=self.request.user)
                .distinct('application'))


class ConnectionDelete(LoginRequiredMixin, DeleteView):
    template_name = 'oauth2_provider/connection_confirm_delete.html'
    success_url = reverse_lazy('connection_list')
    success_message = ('The application authorization has been successfully '
                       'revoked.')

    def _refresh_token_queryset(self, user, application_id):
        return RefreshToken.objects.filter(user=user,
                                           application_id=application_id)

    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)

        refresh_token = self._refresh_token_queryset(self.request.user,
                                                     pk).first()
        if not refresh_token:
            raise Http404("No application connection found.")

        return refresh_token.application

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        token_list = self._refresh_token_queryset(self.request.user,
                                                  self.object.id)

        for refresh_token in token_list:
            refresh_token.revoke()

        messages.success(self.request, self.success_message)

        return HttpResponseRedirect(success_url)
