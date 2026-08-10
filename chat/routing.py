from django.urls import re_path
from . import consumers

# defines a list of URL routes specifically for WebSocket connections
# the list below will be used by the URLRouter in ASGI config (asgi.py)
websocket_urlpatterns = [
    # consumers.ChatConsumer.as_asgi() to convert the ChatConsumer class into an ASGI-compatible application
    # as_asgi() is required because ASGI expects a callable, not a class
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]

# Extra Note
# ws://127.0.0.1:8000/ws/chat/ --> use this url...
# to test web socket connection using PostMan
# need to include "origin"(key) 127.0.0.1(value) in the header
# solution link: https://stackoverflow.com/questions/74867332/websocket-django-channels-doesnt-work-with-postman