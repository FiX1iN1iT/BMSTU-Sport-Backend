from bmstu_app.minio import add_pic, delete_pic
from bmstu_app.models import Section, SportApplication, Priority, CustomUser
from bmstu_app.permissions import IsAdmin, IsManager
from bmstu_app.serializers import UserSerializer, SectionSerializer, SportApplicationSerializer
from bmstu_app.schemas import section_response_schema, sport_application_response_schema

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

import redis

from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

import uuid


session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


@swagger_auto_schema(
    operation_summary="Аутентификация",
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['email', 'password']
    ),
)
@api_view(['POST'])
def login_view(request):
    email = request.data["email"] 
    password = request.data["password"]
    user = authenticate(request, email=email, password=password)
    if user is not None:
        random_key = str(uuid.uuid4())
        session_storage.set(random_key, user.pk)

        serializer = UserSerializer(user)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response.set_cookie("session_id", random_key)
        return response

    else:
        return HttpResponse("{'status': 'error', 'error': 'login failed'}")

@swagger_auto_schema(
    method='post',
    operation_summary="Деавторизация"
)
@api_view(['POST'])
def logout_view(request):
    session_id = request.COOKIES.get('session_id')
    if session_id:
        session_storage.delete(session_id)  # Удалите из вашего хранилища
        response = Response({"message": "Вы вышли из системы."}, status=status.HTTP_200_OK)
        response.delete_cookie("session_id")  # Удалите куку
        return response
    return Response({"error": "Необходима аутентификация."}, status=status.HTTP_401_UNAUTHORIZED)


class UserViewSet(viewsets.ModelViewSet):
    """Класс, описывающий методы работы с пользователями
    Осуществляет связь с таблицей пользователей в базе данных
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    model_class = CustomUser

    def get_permissions(self):
        if self.action in ['create', 'update', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsAdmin | IsManager]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    @swagger_auto_schema(
        operation_summary="Регистрация"
    )
    def create(self, request):
        """
        Функция регистрации новых пользователей
        Если пользователя c указанным в request email ещё нет, в БД будет добавлен новый пользователь.
        """
        if self.model_class.objects.filter(email=request.data['email']).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            new_user = self.model_class.objects.create_user(email=serializer.data['email'],
                                     password=serializer.data['password'],
                                     is_superuser=serializer.data['is_superuser'],
                                     is_staff=serializer.data['is_staff'])
            response_data = serializer.data
            response_data['id'] = new_user.id

            print(response_data)
            return Response(response_data, status=200)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_summary="Обновление данных пользователя"
    )
    def update(self, request, *args, **kwargs):
        """
        Функция обновления данных существующего пользователя.
        Обновляет информацию пользователя по ID, переданному в URL.
        """
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is not None:
                serializer = self.serializer_class(instance=user_instance, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    if 'password' in request.data:
                        user_instance.set_password(request.data['password'])
                    updated_user = self.serializer_class(user_instance)

                    return Response(updated_user.data, status=status.HTTP_200_OK)
                return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "No such user"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "ssid is nil or empty."}, status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        operation_summary="Получение данных пользователя"
    )
    def read(self, request, *args, **kwargs):
        """
        Метод для получения данных о пользователе по его ID.
        """
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is not None:
                serializer = self.serializer_class(user_instance)
                if serializer.is_valid():
                    serializer.save()  # сохраняем обновленные данные
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "No such user"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "ssid is nil or empty."}, status=status.HTTP_403_FORBIDDEN)
    
def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes        
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator


class SectionList(APIView):
    section_class = Section
    section_serializer = SectionSerializer
    application_class = SportApplication
    application_serializer = SportApplicationSerializer

    @swagger_auto_schema(
        operation_summary="Список секций",
        manual_parameters=[
            openapi.Parameter(
                'section_title',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'sections': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=section_response_schema,
                        ),
                        'draft_application_id': openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        'number_of_sections': openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    }
                )
            )
        }
    )
    def get(self, request, format=None):
        sections = self.section_class.objects.filter(is_deleted=False)  
        section_title = request.query_params.get('section_title')
        if section_title:
            sections = sections.filter(title__icontains=section_title)      
        serializer = self.section_serializer(sections, many=True)

        draft_application = None
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is not None:
                draft_application = self.application_class.objects.filter(user=user_instance, status='draft').first()

        draft_application_id = 0
        number_of_sections = 0
        if draft_application is not None:
            draft_application_id = draft_application.id
            number_of_sections = len(Priority.objects.filter(application=draft_application))

        return Response({'sections': serializer.data, 'draft_application_id': draft_application_id, 'number_of_sections': number_of_sections})

    @swagger_auto_schema(
        operation_summary="Добавление секции"
    )
    def post(self, request, format=None):
        serializer = self.section_serializer(data=request.data)
        if serializer.is_valid():
            section = serializer.save()
            image = request.FILES.get("image")
            pic_result = add_pic(section, image)
            if 'error' in pic_result.data:
                return pic_result
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_summary="Одна секция"
)
@api_view(["Get"])
def get_section_details(application, section_id, format=None):
    section = get_object_or_404(Section, pk=section_id)
    serializer = SectionSerializer(section)
    return Response(serializer.data)

@swagger_auto_schema(
    operation_summary="Изменение секции",
    method='put', 
    request_body=SectionSerializer
)
@api_view(["PUT"])
def change_section_details(application, section_id, format=None):
    section = get_object_or_404(Section, pk=section_id)
    serializer = SectionSerializer(section, data=application.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_summary="Удаление секции"
)
@api_view(["DELETE"])
def delete_section(application, section_id, format=None):
    section = get_object_or_404(Section, pk=section_id)
    section.is_deleted = True
    section.save()
    pic_result = delete_pic(section_id)
    if 'error' in pic_result.data:
        return pic_result
    return Response(status=status.HTTP_204_NO_CONTENT)

@swagger_auto_schema(
    method='post',
    operation_summary="Добавление изображения"
)
@api_view(["Post"])
def add_picture_for_section(application, section_id, format=None):
    section = get_object_or_404(Section, pk=section_id)

    new_image = application.FILES.get('image')
    if not new_image:
        return Response({"error": "Изображение не предоставлено."}, status=status.HTTP_400_BAD_REQUEST)

    delete_result = delete_pic(section_id)
    if 'error' in delete_result.data:
        return add_result

    add_result = add_pic(section, new_image)
    if 'error' in add_result.data:
        return add_result

    return Response({"message": "Изображение успешно обновлено."}, status=status.HTTP_200_OK)


class ApplicationList(APIView):
    model_class = SportApplication
    serializer_class = SportApplicationSerializer

    @swagger_auto_schema(
        operation_summary="Список заявок",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'apply_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Response(
                examples={
                    'application/json': {
                        'applications': [
                            {
                                "pk": 2,
                                "status": "created",
                                "creation_date": "2024-10-22T22:27:30Z",
                                "apply_date": None,
                                "end_date": None,
                                "creator": "test@gmail.com",
                                "moderator": "fix1in1it@gmail.com",
                                "full_name": None,
                                "number_of_sections": None
                            }
                        ]
                    }
                },
                description="",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'applications': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=sport_application_response_schema,
                        )
                    }
                )
            )
        }
    )
    def get(self, request, format=None):
        applications = None
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is not None:
                if user_instance.is_staff:
                    applications = self.model_class.objects.all().exclude(status__in=['deleted', 'draft'])
                else:
                    applications = self.model_class.objects.filter(user=user_instance).exclude(status__in=['deleted', 'draft'])
            else:
                return Response({"error": "no such user."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "ssid is nil or empty."}, status=status.HTTP_403_FORBIDDEN)

        query_status = request.query_params.get('status')
        apply_date = request.query_params.get('apply_date')

        if query_status:
            applications = applications.filter(status=query_status)
        if apply_date:
            apply_date_datetime = timezone.datetime.fromisoformat(apply_date)
            applications = applications.filter(apply_date__date=apply_date_datetime)

        serializer = self.serializer_class(applications, many=True)

        return Response({'applications': serializer.data})


class ApplicationDraft(APIView):
    model_class = SportApplication
    serializer_class = SportApplicationSerializer
    
    @swagger_auto_schema(
        operation_summary="Добавление в заявку-черновик",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'section_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            },
            required=['section_id']
        ),
        responses={
            201: openapi.Response('Created'),
            400: openapi.Response('Bad Request')
        }
    )
    def post(self, request, format=None):
        draft_application = None
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is not None:
                draft_application, created = SportApplication.objects.get_or_create(user=user_instance, status='draft', defaults={'creation_date': timezone.now})
            else:
                return Response({"error": "No such user"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "ssid is nil or empty."}, status=status.HTTP_403_FORBIDDEN)
        
        section_id = request.data.get('section_id')
        section = get_object_or_404(Section, pk=section_id, is_deleted=False)

        if Priority.objects.filter(application=draft_application, section=section):
            return Response({"error": "Секция уже добавлена в текущую заявку"}, status=status.HTTP_400_BAD_REQUEST)

        current_priority = len(Priority.objects.filter(application=draft_application)) + 1
        Priority.objects.create(application=draft_application, section=section, priority=current_priority)

        return Response({"draft_application_id": draft_application.pk}, status=status.HTTP_201_CREATED)


class ApplicationDetail(APIView):
    section_class = Section
    section_serializer = SectionSerializer
    application_class = SportApplication
    application_serializer = SportApplicationSerializer

    @swagger_auto_schema(
        operation_summary="Одна заявка",
        responses={
            200: openapi.Response(
                description="",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'application': sport_application_response_schema,
                        'sections': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=section_response_schema,
                        )
                    }
                )
            )
        }
    )
    def get(self, request, application_id, format=None):
        application = get_object_or_404(self.application_class, pk=application_id)
        serializer = self.application_serializer(application)

        priorities = Priority.objects.filter(application=application).order_by('priority')

        sections = []
        for priority in priorities:
            if priority.section.is_deleted == False:
                sections.append(priority.section)
        serialized_sections = self.section_serializer(sections, many=True)

        return Response({'application': serializer.data, 'sections': serialized_sections.data})

    @swagger_auto_schema(
        request_body=SportApplicationSerializer,
        operation_summary="Изменение доп. полей заявки",
    )
    def put(self, request, application_id, format=None):
        application = get_object_or_404(self.application_class, pk=application_id)
        serializer = self.application_serializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Удаление заявки",
        responses={
            204: openapi.Response('No Content'),
        }
    )
    def delete(self, request, application_id, format=None):
        application = get_object_or_404(self.application_class, pk=application_id)
        application.status = 'deleted'
        application.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationSubmit(APIView):
    model_class = SportApplication
    serializer_class = SportApplicationSerializer

    @swagger_auto_schema(
        operation_summary="Сформировать создателем",
        responses={
            204: openapi.Response('No Content'),
            400: openapi.Response('Bad Request')
        }
    )
    def put(self, request, application_id, format=None):
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is None:
                return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                application = get_object_or_404(self.model_class, pk=application_id)
                if application.user != user_instance:
                    return Response({"error": "Заявка может быть сформирована только создателем"}, status=status.HTTP_400_BAD_REQUEST)
                if application.status != 'draft':
                    return Response({"error": "Заявка может быть сформирована только из статуса 'черновик'"}, status=status.HTTP_400_BAD_REQUEST)
                application.status = 'created'
                application.apply_date = timezone.now().isoformat()
                application.save()
                return Response({"message": "Заявка сформирована"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'error': 'No user'}, status=status.HTTP_400_BAD_REQUEST)
    

class ApplicationApproveReject(APIView):
    model_class = SportApplication
    serializer_class = SportApplicationSerializer

    @swagger_auto_schema(
        operation_summary="Завершить/отклонить модератором",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description="'completed' or 'rejected'")
            },
            required=['status']
        ),
        responses={
            200: openapi.Response('Success', serializer_class),
            400: openapi.Response('Bad Request')
        }
    )
    def put(self, request, application_id, format=None):
        ssid = request.COOKIES.get("session_id")
        if ssid is not None:
            user_id = session_storage.get(ssid)
            user_instance = CustomUser.objects.filter(pk=user_id).first()
            if user_instance is None:
                return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)
            if user_instance.is_staff is False:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"error": "ssid is nil or empty."}, status=status.HTTP_403_FORBIDDEN)
        application = get_object_or_404(self.model_class, pk=application_id)
        if application.status != 'created':
            return Response({'error': 'Заявка не может быть завершена до того, как перейдет в статус "Сформирована"'}, status=status.HTTP_400_BAD_REQUEST)
        application.status = request.data['status']
        application.moderator = user_instance
        application.end_date = timezone.now().isoformat()

        priorities = Priority.objects.filter(application=application)

        counter = 0
        for priority in priorities:
            if priority.section.is_deleted == False:
                counter += 1

        application.number_of_sections = counter

        application.save()
        serializer = self.serializer_class(application)

        return Response(serializer.data)


class ApplicationPriority(APIView):
    @swagger_auto_schema(
        operation_summary="Удалить секцию из заявки"
    )
    def delete(self, request, application_id, section_id, format=None):
        application = get_object_or_404(SportApplication, pk=application_id)
        section = get_object_or_404(Section, pk=section_id)
        priority_to_delete = get_object_or_404(Priority, application=application, section=section)
        priority_value = priority_to_delete.priority
        priority_to_delete.delete()

        priorities = Priority.objects.filter(application=application)

        for priority in priorities:
            if priority.priority > priority_value:
                priority.priority -= 1
                priority.save()

        return Response({"message": "Приоритет удален"}, status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(
        operation_summary="Уменьшить значение приоритета секции в заявке"
    )
    def put(self, request, application_id, section_id, format=None):
        application = get_object_or_404(SportApplication, pk=application_id, status='draft')
        section = get_object_or_404(Section, pk=section_id)

        priority_to_change = get_object_or_404(Priority, application=application, section=section)
        if priority_to_change.priority == 1: return Response({"error": "Приоритет уже максимальный"}, status=status.HTTP_400_BAD_REQUEST)
        priority_to_be_changed_with = get_object_or_404(Priority, application=application, priority=priority_to_change.priority - 1)

        old_priority_value = priority_to_change.priority
        priority_to_change.priority = old_priority_value - 1
        priority_to_change.save()

        priority_to_be_changed_with.priority = old_priority_value
        priority_to_be_changed_with.save()

        return Response({"message": "Приоритеты изменены"}, status=status.HTTP_204_NO_CONTENT)
