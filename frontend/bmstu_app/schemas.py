from drf_yasg import openapi

section_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'pk': openapi.Schema(type=openapi.TYPE_INTEGER),
        'title': openapi.Schema(type=openapi.TYPE_STRING),
        'description': openapi.Schema(type=openapi.TYPE_STRING),
        'location': openapi.Schema(type=openapi.TYPE_STRING),
        'date': openapi.Schema(type=openapi.TYPE_STRING),
        'instructor': openapi.Schema(type=openapi.TYPE_STRING),
        'duration': openapi.Schema(type=openapi.TYPE_INTEGER),
        'imageUrl': openapi.Schema(type=openapi.TYPE_STRING),
    }
)

sport_application_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'pk': openapi.Schema(type=openapi.TYPE_INTEGER),
        'status': openapi.Schema(type=openapi.TYPE_STRING),
        'creation_date': openapi.Schema(type=openapi.TYPE_STRING),
        'apply_date': openapi.Schema(type=openapi.TYPE_STRING),
        'end_date': openapi.Schema(type=openapi.TYPE_STRING),
        'creator': openapi.Schema(type=openapi.TYPE_STRING),
        'moderator': openapi.Schema(type=openapi.TYPE_INTEGER),
        'full_name': openapi.Schema(type=openapi.TYPE_STRING),
        'number_of_sections': openapi.Schema(type=openapi.TYPE_STRING),
    }
)
