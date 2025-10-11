from django.conf import settings
from django.http import JsonResponse

def verify_internal_request(func):
    def wrapper(self, request, *args, **kwargs):
        secret = request.headers.get("X-Internal-Secret")
        if secret != settings.INTERNAL_SECRET_KEY:
            return JsonResponse({"error": "Forbidden"}, status=403)
        return func(self, request, *args, **kwargs)
    return wrapper
