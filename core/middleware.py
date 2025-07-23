from django.middleware.csrf import get_token
from django.utils.deprecation import MiddlewareMixin

class CSRFMiddleware(MiddlewareMixin):
    """Middleware to ensure CSRF token is available in cookies"""
    
    def process_response(self, request, response):
        # Ensure CSRF token is in cookies for AJAX requests
        if not request.COOKIES.get('csrftoken'):
            get_token(request)
        return response 