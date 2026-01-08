
from django.contrib import admin
from django.urls import path
from home.views import index

urlpatterns = [
    path('',index,name='index'),

]
"the index is the function name fetched from views.py file in home app, you have to import itfrom home.views import index"