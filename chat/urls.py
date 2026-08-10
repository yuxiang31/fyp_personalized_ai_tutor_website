from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('logout/', views.logout_view, name="logout"), 
    path('create-conversation/', views.create_conversation, name='create_conversation'),
    path('conversation/<str:thread_id>', views.get_conversation_history, name="fetch_conversation"),
    path('conversation/<str:thread_id>/delete/', views.delete_conversation, name='delete_conversation'),
]
