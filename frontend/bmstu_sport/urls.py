from bmstu_app import views

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from graphene_django.views import GraphQLView

from rest_framework import routers, permissions

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'user', views.UserViewSet, basename='user')

class CustomGraphQLView(GraphQLView):
    def execute_graphql_request(self, request, *args, **kwargs):
        # Ensure request.response exists and is valid
        if not hasattr(request, "response"):
            request.response = JsonResponse({})
        return super().execute_graphql_request(request, *args, **kwargs)

    def get_response(self, request, data, show_graphiql=False):
        response = super().get_response(request, data, show_graphiql)

        # Ensure request.response is a proper HttpResponse
        if hasattr(request, "response") and not isinstance(request.response, tuple):
            for cookie in request.response.cookies.values():
                response.cookies[cookie.key] = cookie
        return response

urlpatterns = [
    # GraphQL
    path("graphql", CustomGraphQLView.as_view(graphiql=True)),

    # Админка
    path('admin/', admin.site.urls),

    # Rest framework
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Auth
    path('api/', include(router.urls)),
    path('login/',  views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # Домен услуги
    path(r'sections/', views.SectionList.as_view(), name='sections-list'),
    path(r'sections/<int:section_id>/', views.get_section_details, name='section-details'),
    path(r'sections/<int:section_id>/delete/', views.delete_section, name='delete-section'),
    path(r'sections/<int:section_id>/change/', views.change_section_details, name='change-section-details'),
    path(r'sections/<int:section_id>/upload_image/', views.add_picture_for_section, name='upload-section-image'),
    path(r'applications/draft/', views.ApplicationDraft.as_view(), name='add-to-draft'),

    # Домен заявки
    path(r'applications/', views.ApplicationList.as_view(), name='applications-list'),
    path(r'applications/<int:application_id>/', views.ApplicationDetail.as_view(), name='application-details'),
    path(r'applications/<int:application_id>/submit/', views.ApplicationSubmit.as_view(), name='application-submit'),
    path(r'applications/<int:application_id>/approve-reject/', views.ApplicationApproveReject.as_view(), name='application-approve-reject'),

    # Домен м-м
    path(r'applications/<int:application_id>/priority/<int:section_id>', views.ApplicationPriority.as_view(), name='application-priority'),
]
