import zoneinfo

from django.utils import timezone

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.timezone:
            tzname = request.user.timezone
        else:
            tzname = request.session.get('django_timezone')

        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()

        return self.get_response(request)
