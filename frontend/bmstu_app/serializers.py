from django.contrib.auth.models import User
from bmstu_app.models import Section, SportApplication
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password", "first_name", "last_name"]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["pk", "title", "description", "location", "date", "instructor", "duration", "imageUrl"]


class SportApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SportApplication
        fields = ["pk", "status", "creation_date", "apply_date", "end_date", "full_name", "number_of_sections"]
