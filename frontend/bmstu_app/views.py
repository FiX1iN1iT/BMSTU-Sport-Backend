from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.http import Http404
from django.db import connection

from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from django.contrib.auth.models import User
from bmstu_app.models import Section, Application, Priority
from bmstu_app.serializers import UserSerializer, SectionSerializer, ApplicationSerializer, PrioritySerializer
from bmstu_app.minio import add_pic, delete_pic

from django.utils import timezone

from django.contrib.auth import authenticate, login, logout


# db


@require_GET
def index(request):
    search_query = request.GET.get('section_title', '')
    all_sections = Section.objects.filter(is_deleted=False)
       
    if search_query:
       all_sections = all_sections.filter(title=search_query)

    default_user = User.objects.get(id=2) # id = 1 is superuser
    user_applications = Application.objects.filter(user=default_user)
    draft_application = user_applications.filter(status='draft').first()

    priorities = Priority.objects.filter(application=draft_application)
    application_sections_size = 0
    for priority in priorities:
        if priority.section.is_deleted is False:
           application_sections_size += 1
    
    context = {
        'sections': all_sections,
        'application': draft_application,
        'application_sections_counter': application_sections_size
    }
    return render(request, 'index.html', context)


@require_GET
def section(request, section_id):
    searched_section = get_object_or_404(Section, pk=section_id)
    
    if searched_section.is_deleted == True:
      return Http404("Секция удалена")
    
    context = {
        'section': searched_section
    }
    return render(request, 'section.html', context)


@require_GET
def application(request, application_id):
    application = get_object_or_404(Application, pk=application_id)

    if application.status != 'draft':
       raise Http404("Заявка не доступна для редактирования")

    priorities = Priority.objects.filter(application=application).order_by('priority')

    application_sections = []
    index = 1
    for priority in priorities:
      if priority.section.is_deleted is False:
        application_sections.append({ 'section': priority.section, 'index': index })
        index += 1

    fio = ''
    if application.full_name is not None:
       fio = application.full_name

    context = {
      'id': application.id,
      'fio': fio,
      'sections': application_sections,
    }

    return render(request, 'application.html', context)


@require_POST
def add_section(request, section_id):
    default_user = User.objects.get(id=2) # id = 1 is superuser
    user_applications = Application.objects.filter(user=default_user)
    draft_application = user_applications.filter(status='draft').first()

    chosen_section = Section.objects.get(pk=section_id)

    if not draft_application:
        draft_application = Application.objects.create(user=default_user, status='draft')

    priorities = Priority.objects.filter(application=draft_application)

    if priorities.filter(section=chosen_section):
       print('Эта секция уже добавлена в заявку')
       return redirect('index')
    
    Priority.objects.create(application=draft_application, section=chosen_section, priority=priorities.count() + 1)

    return redirect('index')


@require_POST
def set_application_deleted(request, application_id):
    application = Application.objects.get(id=application_id)
    priorities_counter = Priority.objects.filter(application=application).count()

    with connection.cursor() as cursor:
        cursor.execute("UPDATE application SET status = 'deleted', number_of_sections = %s WHERE id = %s", [priorities_counter, application_id])
        print("Заявка удалена.")
        
    return redirect('index')


# api ex


class SectionList(APIView):
    model_class = Section
    serializer_class = SectionSerializer

    # Возвращает список секций
    def get(self, request, format=None):
        sections = self.model_class.objects.all()
        serializer = self.serializer_class(sections, many=True)
        return Response(serializer.data)

    # Добавляет новую секцию
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            section = serializer.save()
            user1 = user()
            # Назначаем создателем заявки польователя user1
            section.user = user1
            section.save()
            pic = request.FILES.get("pic")
            pic_result = add_pic(section, pic)
            # Если в результате вызова add_pic результат - ошибка, возвращаем его.
            if 'error' in pic_result.data:    
                return pic_result
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SectionDetail(APIView):
    model_class = Section
    serializer_class = SectionSerializer

    # Возвращает информацию о секции
    def get(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        serializer = self.serializer_class(section)
        return Response(serializer.data)

    # Обновляет информацию о секции (для модератора)
    def put(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        serializer = self.serializer_class(section, data=request.data, partial=True)
        if 'pic' in serializer.initial_data:
            pic_result = add_pic(section, serializer.initial_data['pic'])
            if 'error' in pic_result.data:
                return pic_result
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Удаляет информацию о секции
    def delete(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Обновляет информацию о секции (для пользователя)    
@api_view(['Put'])
def put(self, request, section_id, format=None):
    section = get_object_or_404(self.model_class, pk=section_id)
    serializer = self.serializer_class(section, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# def user():
#     try:
#         user1 = User.objects.get(id=2) # id = 1 is superuser
#     except:
#         print("No such user")
#         # user1 = User(id=1, first_name="Иван", last_name="Иванов", password=1234, username="user1")
#         # user1.save()
#     return user1


# class UsersList(APIView):
#     model_class = User
#     serializer_class = UserSerializer

#     def get(self, request, format=None):
#         user = self.model_class.objects.all()
#         serializer = self.serializer_class(user, many=True)
#         return Response(serializer.data)


# my api


def user():
    try:
        user1 = User.objects.get(id=2) # id = 1 is superuser
    except:
        print("No such user")
    return user1


class SectionList(APIView):
    section_class = Section
    section_serializer = SectionSerializer
    application_class = Application
    application_serializer = ApplicationSerializer

    def get(self, request, format=None):
        sections = self.section_class.objects.filter(is_deleted=False)        
        serializer = self.section_serializer(sections, many=True)

        draft_application = self.application_class.objects.get(user=user(), status='draft')
        draft_application_id = ""
        if draft_application is not None:
            draft_application_id = draft_application.id

        return Response({'sections': serializer.data, 'draft_application_id': draft_application_id})

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


class SectionDetail(APIView):
    model_class = Section
    serializer_class = SectionSerializer

    def get(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        serializer = self.serializer_class(section)
        return Response(serializer.data)

    def put(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        serializer = self.serializer_class(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)
        section.is_deleted = True
        section.save()
        pic_result = delete_pic(section_id)
        if 'error' in pic_result.data:
            return pic_result
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def post(self, request, section_id, format=None):
        section = get_object_or_404(self.model_class, pk=section_id)

        new_image = request.FILES.get('image')
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
    model_class = Application
    serializer_class = ApplicationSerializer

    def get(self, request, format=None):
        user_instance = user()
        username = request.data['username']
        searched_user = User.objects.get(username=username)
        if user_instance.is_staff == True:
            applications = self.model_class.objects.filter(user=searched_user, moderator=user_instance).exclude(status__in=['deleted', 'draft'])
            serializer = self.serializer_class(applications, many=True)
            return Response(serializer.data)
        elif user_instance.username == username:
                applications = self.model_class.objects.filter(user=user_instance).exclude(status__in=['deleted', 'draft'])
                serializer = self.serializer_class(applications, many=True)
                return Response(serializer.data)
        else:
            return Response({"error": "Нет доступа к заявкам этого пользователя."}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request, format=None):
        user_instance = user()
        draft_application, created = Application.objects.get_or_create(user=user_instance, status='draft', defaults={'creation_date': timezone.now})
        
        section_id = request.data.get('section_id')
        section = get_object_or_404(Section, pk=section_id, is_deleted=False)

        if Priority.objects.filter(application=draft_application, section=section) is not None:
            return Response({"error": "Секция уже добавлена в текущую заявку"}, status=status.HTTP_400_BAD_REQUEST)

        current_priority = len(Priority.objects.filter(application=draft_application)) + 1
        Priority.objects.create(application=draft_application, section=section, priority=current_priority)

        return Response({"message": "Секция добавлена в заявку"}, status=status.HTTP_201_CREATED)


class ApplicationDetail(APIView):
    section_class = Section
    section_serializer = SectionSerializer
    application_class = Application
    application_serializer = ApplicationSerializer

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

    def put(self, request, application_id, format=None):
        application = get_object_or_404(self.application_class, pk=application_id)
        serializer = self.application_serializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, application_id, format=None):
        application = get_object_or_404(self.application_class, pk=application_id)
        application.status = 'deleted'
        application.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationSubmit(APIView):
    model_class = Application
    serializer_class = ApplicationSerializer

    def put(self, request, application_id, format=None):
        application = get_object_or_404(self.model_class, pk=application_id)
        application.status = 'created'
        application.apply_date = timezone.now
        application.save()
        return Response({"message": "Заявка сформирована"}, status=status.HTTP_204_NO_CONTENT)
    

class ApplicationApproveReject(APIView):
    model_class = Application
    serializer_class = ApplicationSerializer

    def put(self, request, application_id, format=None):
        user_instance = user()
        if user_instance.is_staff == False:
            return Response({'error': 'Текущий пользователь не является модератором'}, status=status.HTTP_403_FORBIDDEN)
        application = get_object_or_404(self.model_class, pk=application_id)
        application.status = request.data['status']
        application.moderator = user_instance
        application.end_date = timezone.now

        priorities = Priority.objects.filter(application=application)

        counter = 0
        for priority in priorities:
            if priority.section.is_deleted == False:
                counter += 1

        application.number_of_sections = counter

        application.save()

        serializer = self.serializer_class(application)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationPriority(APIView):
    model_class = Application
    serializer_class = ApplicationSerializer

    def delete(self, request, application_id, format=None):
        application = get_object_or_404(self.model_class, pk=application_id)
        section_id = request.data['section_id']
        section = Section.objects.get(pk=section_id)
        priority_to_delete = Priority.objects.get(application=application, section=section)
        priority_value = priority_to_delete.priority
        priority_to_delete.delete()

        priorities = Priority.objects.filter(application=application)

        for priority in priorities:
            if priority.priority > priority_value:
                priority.priority -= 1
                priority.save()

        return Response({"message": "Приоритет удален"}, status=status.HTTP_204_NO_CONTENT)
    
    def put(self, request, application_id, format=None):
        application = get_object_or_404(self.model_class, pk=application_id)
        section_id = request.data['section_id']
        new_priority_value = request.data['priority_value']
        section = Section.objects.get(pk=section_id)

        priority_to_change = Priority.objects.get(application=application, section=section)
        old_priority_value = priority_to_change.priority
        priority_to_change.priority = new_priority_value
        priority_to_change.save()

        priority_to_be_changed_with = Priority.objects.filter(application=application, priority=new_priority_value).exclude(section=section).first()
        priority_to_be_changed_with.priority = old_priority_value
        priority_to_be_changed_with.save()

        return Response({"message": "Приоритеты изменены"}, status=status.HTTP_204_NO_CONTENT)
    

class UserProfile(APIView):
    model_class = User
    serializer_class = UserSerializer

    def put(self, request, format=None):
        user_instance = user()
        serializer = self.serializer_class(user_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserLogin(APIView):    
    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({"message": "Вход успешен."}, status=status.HTTP_200_OK)
        return Response({"error": "Неверные данные."}, status=status.HTTP_401_UNAUTHORIZED)


class UserRegistration(APIView):
    serializer_class = UserSerializer
    
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Регистрация успешна."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserLogout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "Выход успешен."}, status=status.HTTP_200_OK)
