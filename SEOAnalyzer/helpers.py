
from django.core.mail import send_mail
import uuid
from django.conf import settings
from django.template.loader import render_to_string

def send_forget_password_mail(email, token):

    reset_link = f"{settings.SITE_URL}/change-password/{token}/"

    context = {
        'reset_link': reset_link
    }

    html_message = render_to_string('forget_password_email.html', context)

    send_mail(
        subject='Reset Your WEB LIFT Password',
        message="Use the link to reset password",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False
    )

    return True
