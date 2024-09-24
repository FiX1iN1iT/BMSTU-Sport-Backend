from django.shortcuts import render
from django.conf import settings

sections = [
  {
  'id': 1,
  'name': 'Футбол для начинающих',
  'description': 'Курс для тех, кто только начинает заниматься футболом.',
  'location': 'Футбольное поле СК',
  'date': 'Понедельник, 16:00',
  'instructor': 'Иванова Елена Петровна',
  'duration': '1,5 часа',
  'imageUrl': 'http://127.0.0.1:9000/bmstu-sport/football.png'
},
  {
  'id': 2,
  'name': 'Баскетбол \'Техника бросков\'',
  'description': 'Курс по совершенствованию техники бросков в баскетболе.',
  'location': 'СК МГТУ',
  'date': 'Среда, 15:00',
  'instructor': 'Иванова Елена Петровна',
  'duration': '1,5 часа',
  'imageUrl': 'http://127.0.0.1:9000/bmstu-sport/basketball.png'
},
  {
  'id': 3,
  'name': 'Хоккей',
  'description': 'Курс по улучшению техники плавания на стиле брасса.',
  'location': 'Измайлово',
  'date': 'Вторник, 12:00',
  'instructor': 'Иванова Елена Петровна',
  'duration': '1,5 часа',
  'imageUrl': 'http://127.0.0.1:9000/bmstu-sport/hockey.png'
},
  {
  'id': 4,
  'name': 'Картинг',
  'description': 'Курс по обучению хип-хоп танцам для детей 6-10 лет.',
  'location': 'Измайлово',
  'date': 'Пятница, 18:00',
  'instructor': 'Иванова Елена Петровна',
  'duration': '1,5 часа',
  'imageUrl': 'http://127.0.0.1:9000/bmstu-sport/racing.png'
},
  {
  'id': 5,
  'name': 'Подготовка к марафону',
  'description': 'Курс для тех, кто только начинает заниматься фитнесом и строить мышцы.',
  'location': 'Манеж СК',
  'date': 'Среда, 13:00',
  'instructor': 'Иванова Елена Петровна',
  'duration': '1,5 часа',
  'imageUrl': 'http://127.0.0.1:9000/bmstu-sport/cycling.png'
},
]

mock_application_1 = {
    'id': 1,
    'fio': '',
    'section_order': [
   {
      'id': 1,
      'id_application': 1,
      'id_section': 1,
      'order_number': 1
   },
   {
      'id': 2,
      'id_application': 1,
      'id_section': 2,
      'order_number': 3
   },
   {
      'id': 3,
      'id_application': 1,
      'id_section': 3,
      'order_number': 2
   },
]
}

def index(request):
    search_query = request.GET.get('section_name', '')
    filtered_sections = [section for section in sections if search_query.lower() in section['name'].lower()]
    application_sections_size = len(mock_application_1['section_order'])
    
    context = {
        'sections': filtered_sections,
        'application': mock_application_1,
        'application_sections_counter': application_sections_size
    }
    return render(request, 'index.html', context)

def section(request, section_id):
    searched_section = None
    for section in sections:
      if section['id'] == section_id:
        searched_section = section
        break
    
    if searched_section == None:
      return
    
    context = {
        'section': searched_section
    }
    return render(request, 'section.html', context)

def application(request, application_id):
    sorted_sections_order = sorted(mock_application_1['section_order'], key=lambda dict: dict['order_number'])

    sorted_sections = []
    index = 0
    for sorted_section_order in sorted_sections_order:
      index += 1
      for section in sections:
        if sorted_section_order['id'] == section['id']:
            sorted_sections.append({ 'section': section, 'index': index })
            break

    context = {
      'id': mock_application_1['id'],
      'fio': mock_application_1['fio'],
      'sections': sorted_sections,
    }

    return render(request, 'application.html', context)
