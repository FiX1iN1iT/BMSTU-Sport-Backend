"""
URL configuration for bmstu_sport project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from bmstu_app import views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Домен услуги
    path(r'sections/', views.SectionList.as_view(), name='sections-list'),
    path(r'sections/<int:section_id>/', views.SectionDetail.as_view(), name='section-details'),
    path(r'sections/<int:section_id>/upload_image/', views.SectionDetail.as_view(), name='upload-section-image'),
    path(r'application/draft/', views.ApplicationList.as_view(), name='add-to-draft'),

    # Домен заявки
    path(r'applications/', views.ApplicationList.as_view(), name='applications-list'),
    path(r'applications/<int:application_id>/', views.ApplicationDetail.as_view(), name='application-details'),
    path(r'applications/<int:application_id>/submit/', views.ApplicationSubmit.as_view(), name='application-submit'),
    path(r'applications/<int:application_id>/approve-reject/', views.ApplicationApproveReject.as_view(), name='application-approve-reject'),

    # Домен м-м
    path(r'applications/<int:application_id>/priority/<int:section_id>', views.ApplicationPriority.as_view(), name='application-priority'),

    # Домен Пользователь
    path(r'register/', views.UserRegistration.as_view(), name='user-registration'),
    path(r'profile/', views.UserProfile.as_view(), name='user-profile'),
    path(r'login/', views.UserLogin.as_view(), name='user-login'),
    path(r'logout/', views.UserLogout.as_view(), name='user-logout'),
]
