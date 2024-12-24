from bmstu_app.minio import add_pic, delete_pic

from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone

import graphene
from graphql import GraphQLError
from graphene_django.types import DjangoObjectType

from .models import Section, SportApplication, Priority, CustomUser

import random

import redis

import uuid


session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


class UpdateApplicationInput(graphene.InputObjectType):
    full_name = graphene.String()

class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'password', 'is_staff', 'is_superuser', 'first_name', 'last_name')

class SportApplicationType(DjangoObjectType):
    user = graphene.Field(UserType)

    class Meta:
        model = SportApplication
        fields = "__all__"

    def resolve_user(self, info):
        return self.user

class ApplicationDraftResponse(graphene.ObjectType):
    draft_application_id = graphene.Int()
    number_of_sections = graphene.Int()

class AddSectionToDraft(graphene.Mutation):
    class Arguments:
        section_id = graphene.Int(required=True)

    response = graphene.Field(ApplicationDraftResponse)

    def mutate(self, info, section_id):
        ssid = info.context.COOKIES.get("session_id")
        user_instance = get_user_from_session(ssid)
        if user_instance is None:
            raise Exception("Unauthorized")

        draft_application, _ = SportApplication.objects.get_or_create(
            user=user_instance, 
            status='draft', 
            defaults={'creation_date': timezone.now}
        )

        section = Section.objects.filter(pk=section_id, is_deleted=False).first()
        if not section:
            raise Exception("Section not found or deleted")

        if Priority.objects.filter(application=draft_application, section=section).exists():
            raise Exception("Section already added to the draft application")

        current_priority = Priority.objects.filter(application=draft_application).count() + 1
        Priority.objects.create(
            application=draft_application, 
            section=section, 
            priority=current_priority
        )

        return AddSectionToDraft(
            response=ApplicationDraftResponse(
                draft_application_id=draft_application.pk, 
                number_of_sections=current_priority
            )
        )


class SectionType(DjangoObjectType):
    class Meta:
        model = Section
        fields = ('id', 'title', 'description', 'location', 'date', 'instructor', 'duration', 'imageUrl')

class Query(graphene.ObjectType):
    section = graphene.Field(SectionType, id=graphene.Int(required=True))
    sections = graphene.List(
        SectionType, 
        section_title=graphene.String(required=False)
    )
    draft_application_id = graphene.Int()
    number_of_sections = graphene.Int()
    applications = graphene.List(
        SportApplicationType,
        status=graphene.String(),
        start_apply_date=graphene.String(),
        end_apply_date=graphene.String()
    )
    application_detail = graphene.Field(
        SportApplicationType,
        application_id=graphene.Int(required=True)
    )
    sections_by_application = graphene.List(
        SectionType,
        application_id=graphene.Int(required=True)
    )


    def resolve_section(self, info, id):
        return Section.objects.get(pk=id)

    def resolve_sections(self, info, section_title=None):
        queryset = Section.objects.filter(is_deleted=False)
        if section_title:
            queryset = queryset.filter(title__icontains=section_title)
        return queryset

    def resolve_draft_application_id(self, info):
        ssid = info.context.COOKIES.get("session_id")
        user = get_user_from_session(ssid)
        if user:
            draft_application = SportApplication.objects.filter(
                user=user, status='draft'
            ).first()
            return draft_application.id if draft_application else 0
        return 0

    def resolve_number_of_sections(self, info):
        ssid = info.context.COOKIES.get("session_id")
        user = get_user_from_session(ssid)
        if user:
            draft_application = SportApplication.objects.filter(
                user=user, status='draft'
            ).first()
            if draft_application:
                return Priority.objects.filter(application=draft_application).count()
        return 0
    
    def resolve_applications(self, info, status=None, start_apply_date=None, end_apply_date=None):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise Exception("Unauthorized")

        if user.is_staff or user.is_superuser:
            applications = SportApplication.objects.all().exclude(status__in=['deleted', 'draft'])
        else:
            applications = SportApplication.objects.filter(user=user).exclude(status__in=['deleted', 'draft'])

        if status:
            applications = applications.filter(status=status)
        if start_apply_date:
            start_apply_datetime = timezone.datetime.fromisoformat(start_apply_date)
            applications = applications.filter(apply_date__date__gte=start_apply_datetime)
        if end_apply_date:
            end_apply_datetime = timezone.datetime.fromisoformat(end_apply_date)
            applications = applications.filter(apply_date__date__lte=end_apply_datetime)

        return applications
    
    def resolve_application_detail(self, info, application_id):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)
        if application.user != user and not user.is_staff:
            raise GraphQLError("Permission denied")

        return application

    def resolve_sections_by_application(self, info, application_id):
        application = SportApplication.objects.get(pk=application_id)
        priorities = Priority.objects.filter(application=application).order_by('priority')

        sections = []
        for priority in priorities:
            if priority.section.is_deleted == False:
                if (application.status == 'completed' or application.status == 'rejected') and not (':' in priority.section.location):
                    priority.section.location = priority.section.location + ": " + priority.classroom + " аудитория"
                sections.append(priority.section)

        return sections

class CreateSection(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)

    section = graphene.Field(SectionType)

    def mutate(self, info, title):
        ssid = info.context.COOKIES.get("session_id")
        moderator = get_moderator_from_session(ssid)
        if moderator:
            section = Section.objects.create(title=title)
            section.save()
            return CreateSection(section=section)

        raise Exception("Unauthorized")
    
class UpdateSection(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        description = graphene.String()
        location = graphene.String()
        date = graphene.String()
        instructor = graphene.String()
        duration = graphene.Int()

    section = graphene.Field(SectionType)

    def mutate(self, info, id, **kwargs):
        ssid = info.context.COOKIES.get("session_id")
        moderator_instance = get_moderator_from_session(ssid)
        if moderator_instance is None:
            raise Exception("Unauthorized")

        section = Section.objects.get(pk=id)
        for key, value in kwargs.items():
            if key in ['date']:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            setattr(section, key, value)
        section.save()

        return UpdateSection(section=section)
    
class DeleteSection(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    success = graphene.Boolean()

    def mutate(self, info, id):
        ssid = info.context.COOKIES.get("session_id")
        moderator_instance = get_moderator_from_session(ssid)
        if moderator_instance is None:
            raise Exception("Unauthorized")

        section = Section.objects.get(pk=id)
        section.is_deleted = True
        section.save()
        delete_pic(section.id)

        return DeleteSection(success=True)
    
class ApplicationApproveReject(graphene.Mutation):
    class Arguments:
        application_id = graphene.String(required=True)
        status = graphene.String(required=True)

    application = graphene.Field(SportApplicationType)

    def mutate(self, info, application_id, status):
        request = info.context
        ssid = request.COOKIES.get("session_id")
        moderator_instance = get_moderator_from_session(ssid)
        if moderator_instance is None:
            raise Exception("Unauthorized")

        application = SportApplication.objects.get(pk=application_id)
        if application.status != 'created':
            raise Exception('Заявка может быть завершена или отклонена только из статуса "Сформирована"')

        application.status = status
        application.moderator = moderator_instance
        application.end_date = timezone.now().isoformat()

        priorities = Priority.objects.filter(application=application)
        unique_classrooms = []
        for priority in priorities:
            if not priority.section.is_deleted:
                new_classroom = str(random.randint(100, 999))
                priority.classroom = new_classroom
                unique_classrooms.append(new_classroom)
                priority.save()

        unique_classrooms = set(unique_classrooms)
        application.number_of_sections = len(unique_classrooms)

        application.save()

        return ApplicationApproveReject(application=application)
    
class UpdateApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.Int(required=True)
        input = UpdateApplicationInput(required=True)

    application = graphene.Field(SportApplicationType)

    def mutate(root, info, application_id, input):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)
        if application.user != user:
            raise GraphQLError("Permission denied")

        if application.status != 'draft':
            raise GraphQLError("Only draft applications can be updated")

        for field, value in input.items():
            setattr(application, field, value)
        application.save()

        return UpdateApplication(application=application)


class DeleteApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.Int(required=True)

    success = graphene.Boolean()

    def mutate(root, info, application_id):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)
        if application.user != user:
            raise GraphQLError("Permission denied")

        application.status = 'deleted'
        application.save()

        return DeleteApplication(success=True)
    
class SubmitApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.Int(required=True)

    success = graphene.Boolean()

    def mutate(root, info, application_id):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)

        if application.user != user:
            raise GraphQLError("Only the creator can submit the application")

        if application.status != 'draft':
            raise GraphQLError("Applications can only be submitted from 'draft' status")

        application.status = 'created'
        application.apply_date = timezone.now().isoformat()
        application.save()

        return SubmitApplication(success=True)


class RemoveSection(graphene.Mutation):
    class Arguments:
        application_id = graphene.Int(required=True)
        section_id = graphene.Int(required=True)

    sections_by_application = graphene.List(SectionType)

    def mutate(root, info, application_id, section_id):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)

        if application.user != user:
            raise GraphQLError("Permission denied")

        section = Section.objects.get(pk=section_id)
        priority_to_delete = Priority.objects.get(application=application, section=section)
        priority_value = priority_to_delete.priority
        priority_to_delete.delete()

        priorities = Priority.objects.filter(application=application)
        for priority in priorities:
            if priority.priority > priority_value:
                priority.priority -= 1
                priority.save()

        priorities = Priority.objects.filter(application=application).order_by("priority")
        sections = [priority.section for priority in priorities if not priority.section.is_deleted]

        return RemoveSection(sections_by_application=sections)


class IncreasePriority(graphene.Mutation):
    class Arguments:
        application_id = graphene.Int(required=True)
        section_id = graphene.Int(required=True)

    sections_by_application = graphene.List(SectionType)

    def mutate(root, info, application_id, section_id):
        user = get_user_from_session(info.context.COOKIES.get("session_id"))

        if not user:
            raise GraphQLError("Authentication required")

        application = SportApplication.objects.get(pk=application_id)

        if application.user != user:
            raise GraphQLError("Permission denied")

        section = Section.objects.get(pk=section_id)
        priority_to_change = Priority.objects.get(application=application, section=section)

        if priority_to_change.priority == 1:
            raise GraphQLError("Priority is already at the maximum level")

        priority_to_be_changed_with = Priority.objects.get(
            application=application,
            priority=priority_to_change.priority - 1
        )

        old_priority_value = priority_to_change.priority
        priority_to_change.priority = old_priority_value - 1
        priority_to_change.save()

        priority_to_be_changed_with.priority = old_priority_value
        priority_to_be_changed_with.save()

        priorities = Priority.objects.filter(application=application).order_by("priority")
        sections = [priority.section for priority in priorities if not priority.section.is_deleted]

        return IncreasePriority(sections_by_application=sections)
    
class LoginMutation(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    user = graphene.Field(UserType)

    def mutate(root, info, email, password):
        request = info.context
        user = authenticate(email=email, password=password)

        if user is None:
            raise GraphQLError("Invalid email or password")

        session_key = str(uuid.uuid4())
        session_storage.set(session_key, user.pk)

        if hasattr(request, "response") and isinstance(request.response, JsonResponse):
            request.response.set_cookie("session_id", session_key)

        return LoginMutation(user=user)


class LogoutMutation(graphene.Mutation):
    success = graphene.Boolean()

    def mutate(root, info):
        session_id = info.context.COOKIES.get("session_id")
        if not session_id:
            raise GraphQLError("No active session found")

        session_storage.delete(session_id)
        info.context.response.delete_cookie("session_id")

        return LogoutMutation(success=True)


class Mutation(graphene.ObjectType):
    approve_reject_application = ApplicationApproveReject.Field()
    create_section = CreateSection.Field()
    update_section = UpdateSection.Field()
    add_section_to_draft = AddSectionToDraft.Field()
    delete_section = DeleteSection.Field()
    update_application = UpdateApplication.Field()
    delete_application = DeleteApplication.Field()
    submit_application = SubmitApplication.Field()
    remove_section = RemoveSection.Field()
    increase_priority = IncreasePriority.Field()
    login = LoginMutation.Field()
    logout = LogoutMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)


def get_user_from_session(ssid):
    if ssid is None:
        return None

    user_id = session_storage.get(ssid)
    user_instance = CustomUser.objects.filter(pk=user_id).first()

    if user_instance is None:
        return None

    return user_instance

def get_moderator_from_session(ssid):
    user_instance = get_user_from_session(ssid)

    if user_instance and (user_instance.is_staff or user_instance.is_superuser):
        return user_instance

    return None
