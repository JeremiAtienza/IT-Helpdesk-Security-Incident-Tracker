"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from filemanager.forms import CustomAuthForm
from filemanager.views import AdminDashboardView
import two_factor.urls as two_factor_urls

urlpatterns = [
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/', admin.site.urls),
    path('accounts/', include((two_factor_urls.urlpatterns[0], 'two_factor'), namespace='two_factor')),
    # Keep classic auth fallback and custom login form for password reset / logout paths
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=CustomAuthForm), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('filemanager.urls')),
]
