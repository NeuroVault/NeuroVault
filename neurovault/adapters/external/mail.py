"""Notifications by email."""
import os

from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

SENDER = "NeuroVault <do_not_reply@neurovault.org>"


class EmailNotifier:
    def notify(self, kind, subject, user_ids, context):
        plain_tpl = os.path.join("email", "%s.txt" % kind)
        html_tpl = os.path.join("email", "%s.html" % kind)
        for user in User.objects.filter(pk__in=list(user_ids)).order_by("pk"):
            ctx = dict(context, username=user.username)
            msg = EmailMultiAlternatives(
                subject, render_to_string(plain_tpl, ctx), SENDER, [user.email]
            )
            msg.attach_alternative(render_to_string(html_tpl, ctx), "text/html")
            msg.send()
