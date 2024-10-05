from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET

from django.http import Http404

from django.db import connection

from django.contrib.auth.models import User
from bmstu_app.models import Section, Application, Priority


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
