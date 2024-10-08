from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.views import APIView

from django.contrib.auth.models import User
from bmstu_app.models import Section, Application, Priority
from bmstu_app.serializers import UserSerializer, SectionSerializer, ApplicationSerializer

from django.contrib.auth import authenticate, login, logout
from bmstu_app.minio import add_pic, delete_pic

from django.utils import timezone


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
        section_title = request.query_params.get('section_title')
        if section_title:
            sections = sections.filter(title__icontains=section_title)      
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
        
        applications = self.model_class.objects.filter(user=searched_user).exclude(status__in=['deleted', 'draft'])
        
        if user_instance.is_staff:
            status = request.query_params.get('status')
            apply_date = request.query_params.get('apply_date')

            if status:
                applications = applications.filter(status=status)
            if apply_date:
                apply_date_datetime = timezone.datetime.fromisoformat(apply_date)
                applications = applications.filter(apply_date__date=apply_date_datetime)

            applications = applications.filter(moderator=user_instance)

        elif user_instance.username == username:
            status = request.query_params.get('status')
            apply_date = request.query_params.get('apply_date')

            if status:
                applications = applications.filter(status=status)
            if apply_date:
                apply_date_datetime = timezone.datetime.fromisoformat(apply_date)
                applications = applications.filter(apply_date__date=apply_date_datetime)

        else:
            return Response({"error": "Нет доступа к заявкам этого пользователя."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(applications, many=True)
        return Response(serializer.data)


    def post(self, request, format=None):
        user_instance = user()
        draft_application, created = Application.objects.get_or_create(user=user_instance, status='draft', defaults={'creation_date': timezone.now})
        
        section_id = request.data.get('section_id')
        section = get_object_or_404(Section, pk=section_id, is_deleted=False)

        if Priority.objects.filter(application=draft_application, section=section):
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
        application.apply_date = timezone.now().isoformat()
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
        if application.status != 'created':
            return Response({'error': 'Заявка не может быть завершена до того, как перейдет в статус "Сформирована"'}, status=status.HTTP_403_FORBIDDEN)
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
        application = get_object_or_404(self.model_class, pk=application_id, status='draft')
        section_id = request.data['section_id']
        new_priority_value = request.data['priority_value']
        section = Section.objects.get(pk=section_id)

        priority_to_change = get_object_or_404(Priority, application=application, section=section)
        priority_to_be_changed_with = get_object_or_404(Priority, application=application, priority=new_priority_value)

        old_priority_value = priority_to_change.priority
        priority_to_change.priority = new_priority_value
        priority_to_change.save()

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
