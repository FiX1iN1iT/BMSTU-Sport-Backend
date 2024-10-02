from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST, require_GET

from django.db import connection

from django.contrib.auth.models import User
from bmstu_app.models import Section, Application, Priority


@require_GET
def index(request):
    search_query = request.GET.get('section_title', '')
    all_sections = Section.objects.all()
       
    if search_query:
       all_sections = all_sections.filter(title=search_query)

    default_user = User.objects.get(id=2) # id = 1 is superuser
    user_applications = Application.objects.filter(user=default_user)
    draft_application = user_applications.filter(status='draft').first()

    application_sections_size = Priority.objects.filter(application=draft_application).count()
    
    context = {
        'sections': all_sections,
        'application': draft_application,
        'application_sections_counter': application_sections_size
    }
    return render(request, 'index.html', context)


@require_GET
def section(request, section_id):
    searched_section = Section.objects.filter(id=section_id).first
    
    if searched_section == None:
      return
    
    context = {
        'section': searched_section
    }
    return render(request, 'section.html', context)


@require_GET
def application(request):
    default_user = User.objects.get(id=2) # id = 1 is superuser
    user_applications = Application.objects.filter(user=default_user)
    draft_application = user_applications.filter(status='draft').first()
    priorities = Priority.objects.filter(application=draft_application).order_by('priority')

    application_sections = []
    for priority in priorities:
      application_sections.append({ 'section': priority.section, 'index': priority.priority })

    fio = ''
    if draft_application.full_name is not None:
       fio = draft_application.full_name

    context = {
      'id': draft_application.id,
      'fio': fio,
      'sections': application_sections,
    }

    return render(request, 'application.html', context)


@require_POST
def add_section(request, section_id):
    default_user = User.objects.get(id=2) # id = 1 is superuser
    user_applications = Application.objects.filter(user=default_user)
    draft_application = user_applications.filter(status='draft').first()

    chosen_section = Section.objects.filter(id=section_id).first()

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
