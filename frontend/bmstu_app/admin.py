from django.contrib import admin
from .models import Section, SportApplication, Priority, CustomUser

admin.site.register(Section)
admin.site.register(SportApplication)
admin.site.register(Priority)
admin.site.register(CustomUser)