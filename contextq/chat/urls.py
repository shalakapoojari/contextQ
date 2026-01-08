from django.urls import path
from . import views
app_name = "chat" 

urlpatterns = [
    path('', views.index, name='index'),
    path('start/', views.start_chat, name='start_chat'),
    path('chat/<uuid:chat_id>/', views.chat_view, name='chat_view'),  # ✅ This must exist
    path('ask/<uuid:chat_id>/', views.ask_question, name='ask_question'),
    path('chat/delete/<uuid:chat_id>/', views.delete_session, name='delete_session'),
]
