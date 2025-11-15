from .models import AuditLog
from django.utils.deprecation import MiddlewareMixin

class AuditMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/static/'):
            return None
        ip = request.META.get('REMOTE_ADDR')
        user = request.user if request.user.is_authenticated else None
        AuditLog.objects.create(
            user=user,
            path=request.path,
            method=request.method,
            ip_address=ip,
        )
        return None
