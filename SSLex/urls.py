"""SSLex URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.urls import path

from App import views

urlpatterns = [
    path("api/reminder/", views.reminder),
    path("", views.index),
    path("api/domain/expiry_date/", views.ssl_expiry),
    path("account/", views.v_account),
    path("account/<domain_unique_id>/", views.v_account),
    path("reminder/", views.v_reminder),
    path("reminder/<str:domain_unique_id>/", views.v_reminder),
    path("reminder/<str:domain_unique_id>/<reminder_id>/", views.v_reminder),
]
