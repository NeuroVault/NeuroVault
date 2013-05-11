from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm,\
    PasswordChangeForm

class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
    
class UserEditForm(UserChangeForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
    
class BlankPasswordChangeForm(PasswordChangeForm):
    
    old_password = forms.CharField(label="Old password",
                                   widget=forms.PasswordInput,
                                   required=False)

    def clean_old_password(self):
        if self.user.has_usable_password():
            return super(BlankPasswordChangeForm, self).clean_old_password()
        else:
            return self.cleaned_data["old_password"]