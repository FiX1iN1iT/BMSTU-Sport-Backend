from django.http import JsonResponse

class AddResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ensure request.response is initialized with a valid HttpResponse
        if not hasattr(request, "response"):
            request.response = JsonResponse({})
        response = self.get_response(request)
        return response
