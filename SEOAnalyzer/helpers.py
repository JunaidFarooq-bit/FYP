
from django.core.mail import send_mail
import uuid
from django.conf import settings
from django.template.loader import render_to_string

def send_forget_password_mail(email, token):
    subject = 'FORGET PASSWORD'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    html_message = render_to_string('forget_password_email.html', {'token': token})
    send_mail(subject, None, email_from, recipient_list, html_message=html_message)
    return True