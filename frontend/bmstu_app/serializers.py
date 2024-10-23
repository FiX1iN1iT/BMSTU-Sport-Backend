from bmstu_app.models import Section, SportApplication, CustomUser
from collections import OrderedDict
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["pk", "title", "description", "location", "date", "instructor", "duration", "imageUrl"]

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 


class SportApplicationSerializer(serializers.ModelSerializer):
    creator = serializers.EmailField(source='user.email', read_only=True)
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = SportApplication
        fields = ["pk", "status", "creation_date", "apply_date", "end_date", "creator", "moderator", "full_name", "number_of_sections"]

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields
        
    def get_moderator(self, obj):
        return obj.moderator.email if obj.moderator else None
