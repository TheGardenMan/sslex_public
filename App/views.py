from datetime import date, datetime
from typing import Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from App import logic
from App.errors import APIError, HTMLError
from App.models import Timezone


def index(request):
    return render(request, "index.html", {"BASE_URL": settings.BASE_URL})


@api_view(["POST"])
def ssl_expiry(request):
    # api_view cleans up and puts JSON data as dict into request.data
    # raise APIError()
    client_data = request.data
    domain_name = client_data.get("domain_name", None)
    user_timezone = client_data.get("user_timezone", None)

    if not domain_name:
        raise APIError(message="Missing domain_name")

    # TODO: handle subdomain https://expired.badssl.com using
    # https://stackoverflow.com/questions/6925825/get-subdomain-from-url-using-python
    valid_domain: bool
    cleaned_domain_name: str
    # whois also does the cleanup for us
    valid_domain, cleaned_domain_name = logic.is_valid_domain(domain_name)
    if not valid_domain:
        raise APIError(message="Invalid or unreachable domain")

    if not user_timezone:
        raise APIError(message="Missing user_timezone")

    try:
        timezone_obj = ZoneInfo(user_timezone)
        Timezone.objects.get_or_create(name=timezone_obj)
    except ZoneInfoNotFoundError:
        raise APIError(message="Invalid user_timezone")
    expiry_date, is_expired = logic.check_ssl_expiry_date(
        cleaned_domain_name, timezone_obj
    )
    return Response(
        {
            "expiry_date": expiry_date.strftime("%dth %B %Y %I:%M %p"),
            "domain_name": cleaned_domain_name,
            "is_expired": is_expired,
        }
    )


@api_view(["POST"])
@renderer_classes([JSONRenderer, TemplateHTMLRenderer])
def reminder(request, domain_unique_id=None, reminder_id=None):
    client_data = request.data

    domain_name = client_data.get("domain_name", None)
    if not domain_name:
        return APIError(message="Missing domain_name ")

    timezone_name = client_data.get("timezone_name", None)
    if not timezone_name:
        return APIError(message="Missing timezone_name")

    try:
        timezone_zoneinfo_obj: ZoneInfo = ZoneInfo(timezone_name)
        timezone_obj: Timezone
        _created: bool
        timezone_obj, _created = Timezone.objects.get_or_create(
            name=timezone_zoneinfo_obj
        )
    except ZoneInfoNotFoundError:
        raise APIError(message="Invalid timezone_name")

    email = client_data.get("email", None)
    if not email:
        raise APIError(message="Missing email")

    reminder_dates = client_data.get("reminder_dates", None)
    if not reminder_dates:
        raise APIError(message="Missing reminder_dates")

    if not isinstance(reminder_dates, list) or len(reminder_dates) > 2:
        raise APIError(message="Wrong reminder_date format or too many dates")

    reminder_datetime_objects = []
    try:
        for reminder_date in reminder_dates:
            # https://stackoverflow.com/a/69261133/14475872
            # get the datetime (hours,mins,sec are 0 now)
            reminder_user_datetime: datetime = datetime.strptime(
                reminder_date, "%Y-%m-%d"
            )
            # hour is 9AM now
            reminder_user_datetime_9_AM = reminder_user_datetime.replace(hour=9)

            # convert it to UTC
            reminder_utc_datetime_in_UTC = reminder_user_datetime_9_AM.astimezone(
                ZoneInfo("UTC")
            )
            reminder_datetime_objects.append(reminder_utc_datetime_in_UTC)
    except ValueError:
        raise APIError(message="Invalid dates in reminder_date")

    # pylint: disable=no-value-for-parameter,E1111
    domain_expiry_date, is_expired = logic.check_ssl_expiry_date(domain_name)
    created_data = logic.create_domain_and_reminder(
        domain_name,
        domain_expiry_date,
        timezone_obj,
        email,
        reminder_datetime_objects,
        client_data,
    )
    return Response({"data": created_data})


@require_GET
def v_reminder(request, domain_unique_id=None, reminder_id=None):
    if not domain_unique_id or not reminder_id:
        raise HTMLError(message="Missing required params")
    logic.delete_reminder(domain_unique_id, reminder_id)
    # https://stackoverflow.com/a/69282393/14475872
    return render(
        request,
        "deleted.html",
        {"message": "Reminder deleted successfully"},
    )


@require_GET
def v_account(request, domain_unique_id=None):
    if not domain_unique_id:
        raise HTMLError(message="Missing account_id")
    logic.delete_account(domain_unique_id)
    return render(
        request,
        "deleted.html",
        {"message": "All data deleted successfully"},
    )
