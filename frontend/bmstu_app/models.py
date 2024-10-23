from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from django.utils import timezone


class NewUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')
        
        email = self.normalize_email(email) 
        user = self.model(email=email, **extra_fields) 
        user.set_password(password)
        user.save(using=self.db)
        return user
    
    def create_superuser(self, email, password, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')
        
        email = self.normalize_email(email) 
        user = self.model(email=email, **extra_fields) 
        user.set_password(password)
        user.save(using=self.db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(("email адрес"), unique=True)
    password = models.CharField(max_length=100, verbose_name="Пароль")    
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")

    USERNAME_FIELD = 'email'

    objects =  NewUserManager()


class Section(models.Model):
    title = models.CharField(max_length=100, null=False)
    description = models.CharField(max_length=500, default="У этой секции нет описания", null=False)
    location = models.CharField(max_length=200, default="СК МГТУ", null=False)
    date = models.DateTimeField(default=timezone.now, null=False)
    instructor = models.CharField(max_length=100, default="Петров Петр Петрович", null=False)
    duration = models.IntegerField(default=90, null=False)
    imageUrl = models.URLField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=False)

    class Meta:
        db_table = 'section'

    def __str__(self):
        return f"Section '{self.id}':  '{self.title}' at '{self.date}'"


class SportApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удалена'),
        ('created', 'Сформирована'),
        ('completed', 'Завершена'),
        ('rejected', 'Отклонена')
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft', null=False)

    creation_date = models.DateTimeField(default=timezone.now, null=False)
    apply_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False, related_name='user')
    moderator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderator')

    full_name = models.CharField(max_length=100, null=True, blank=True)
    number_of_sections = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'application'

    def __str__(self):
        return f"Application '{self.id}' by '{self.user.email}' created at '{self.creation_date}'"


class Priority(models.Model):
    application = models.ForeignKey(SportApplication, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)

    priority = models.IntegerField()

    class Meta:
        db_table = 'priority'
        unique_together = ('application', 'section')

    def __str__(self):
        return f"Priority '{self.id}' in '{self.application}' of '{self.section}' = '{self.priority}'"
