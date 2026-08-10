"""
ASGI config for Personalized_AI_Tutor_Website project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import chat.routing 

# code below is to tell Django which settings file to use
# required before you can run Django applications, including ASGI(Asynchronous Server Gateway Interface)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Personalized_AI_Tutor_Website.settings')

# prepare Django app to serve over ASGI
# enables handling of traditional HTTP requests through ASGI
django_asgi_app = get_asgi_application()

# to route different protocol types - HTTP and WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app, # --> HTTP requests are handled by standard Django app
    "websocket": AllowedHostsOriginValidator( # --> verifies that incoming WebSocket connections come from allowed hosts (based on "ALLOWED_HOSTS") in settings
        AuthMiddlewareStack( # --> wraps the connection in Django's authentication middleware
            URLRouter( # --> routes WebSocket connections to different consumers based on their URL
                chat.routing.websocket_urlpatterns # --> need to be define in chat/routing.py
            )
        )
    ),
})
