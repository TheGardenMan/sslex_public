import json
import socket
import ssl
from datetime import datetime, timedelta
from http.client import HTTPSConnection
from typing import Tuple
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import OpenSSL
import requests
import whois
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet
from fake_useragent import UserAgent

from App import consumer

# from rest_framework.exceptions import APIError
from App.errors import APIError, HTMLError
from App.models import Domain, DummyDomain, Reminder, Timezone
from django.conf import settings

user_agent_generator = UserAgent()

# https://www.ssl.com/sample-valid-revoked-and-expired-ssl-tls-certificates/


def capture_exception(exception: Exception):
    if not settings.DEBUG:
        import sentry_sdk

        sentry_sdk.capture_exception(exception)


def is_valid_domain(domain_name: str) -> Tuple[bool, str]:
    try:
        whois_response = whois.whois(domain_name)
        if whois_response["domain_name"]:
            return True, whois_response["domain_name"][1]
        return False, ""
    except whois.parser.PywhoisError:
        return False, ""


def check_https_url(domain_name: str):
    #     HTTPS_URL = f"https://{domain_name}"
    #     try:
    #         HTTPS_URL = urlparse(HTTPS_URL)
    #         connection = HTTPSConnection(HTTPS_URL.netloc, timeout=2)
    #         connection.request("HEAD", HTTPS_URL.path)
    #         if connection.getresponse():
    #             return True
    #         else:
    #             return False
    #     except ssl.SSLCertVerificationError:
    # return False
    pass


def get_ssl_expiry_date(
    hostname: str, user_timezone: str = None
) -> Tuple[datetime, bool]:
    """
    Get number of days before an TLS/SSL of a domain expired
    """
    port = 443
    context = ssl.SSLContext()
    with socket.create_connection((hostname, port), timeout=1) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            certificate = ssock.getpeercert(True)
            cert = ssl.DER_cert_to_PEM_cert(certificate)
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
            cert_expires_UTC = datetime.strptime(
                x509.get_notAfter().decode("utf-8"), "%Y%m%d%H%M%S%z"
            )
            is_expired = (
                False
                if (datetime.utcnow().astimezone(ZoneInfo("UTC")) < cert_expires_UTC)
                else True
            )
            if user_timezone:
                cert_expires_USER_TIMEZONE = cert_expires_UTC.astimezone(user_timezone)
                return cert_expires_USER_TIMEZONE, is_expired
            return cert_expires_UTC, is_expired


def is_https_supported_2(domain_name: str) -> bool:
    """Using SSL connection to create a certificate"""
    host = (domain_name, 443)
    purpose = ssl.Purpose.SERVER_AUTH
    context = ssl.create_default_context(purpose=purpose)
    try:
        with socket.create_connection(host, timeout=1) as sock:
            with context.wrap_socket(sock, server_hostname=host[0]) as wrapped:
                pass
    except ssl.SSLCertVerificationError as error:
        # rest of the exceptions are handled in check_ssl_expiry_date()
        error_msg = str(error)
        if "not valid" in error_msg:
            return False
        elif "expired" in error_msg:
            return True
    # HTTPS connection was successful
    return True


def is_https_supported(domain_name: str):
    #     """Using naive 301 redirect"""
    #     HTTP_URL = f"http://{domain_name}"
    #     # Responses append "/" in Location during redirect
    #     HTTPS_URL = f"https://{domain_name}/"
    #     headers = {"User-Agent": str(user_agent_generator.random)}
    #     response = requests.head(HTTP_URL, timeout=1, headers=headers)
    #     # Some sites don't redirect to HTTPS when trying to access HTTP.
    #     # Edge case and NOT MY PROBLEM
    #     # When too many requests get sent to google in same time,
    #     # response.headers["Location"] is not equal to HTTPS_URL.
    #     # So I have removed that check here below.
    #     # if response.status_code == 301 or response.status_code == 308
    #     # and response.headers["Location"] == HTTPS_URL:
    #     if response.status_code == 301 or response.status_code == 308:
    #         print(HTTP_URL + " supports HTTPS")
    #         return True
    #     elif str(response.status_code.startswith("4")):
    #         pass
    #     elif str(response.status_code.startswith("5")):
    #         pass
    pass


def check_ssl_expiry_date(domain_name: str, user_timezone: str = None) -> datetime:
    try:
        if is_https_supported_2(domain_name):
            try:
                DummyDomain.objects.create(domain_name=domain_name)
            except:
                pass
            return get_ssl_expiry_date(domain_name, user_timezone)
        raise APIError(message="This site doesn't support HTTPS")
    except requests.exceptions.ConnectionError:
        # unreachable
        raise APIError(message="This site is unreachable")
    except requests.exceptions.Timeout:
        # during timeout
        raise APIError(message="Request timed out while" " trying to reach the server")
    except requests.exceptions.TooManyRedirects:
        # Redirect loop
        raise APIError(message="Too Many Redirects")
    except socket.timeout:
        # during timeout
        raise APIError(message="Request timed out while" " trying to reach the server")
    except socket.gaierror:
        # during DNS failure
        raise APIError(message="This site is unreachable")


def create_domain_and_reminder(
    domain_name: str,
    domain_expiry_date: datetime,
    timezone_obj: Timezone,
    email: str,
    reminder_datetime_objects: list,
    client_data: dict,
):

    created_data = {}
    with transaction.atomic():
        domain_obj: Domain = Domain.objects.create(
            domain_name=domain_name, request_body=json.dumps(client_data)
        )
        created_data["account"] = domain_obj.domain_unique_id
        reminder_ids = []

        print("===================================================================")
        for reminder_datetime_obj in reminder_datetime_objects:
            reminder_obj: Reminder = Reminder.objects.create(
                email=email,
                expiry_date=domain_expiry_date,
                remind_at=reminder_datetime_obj,
                timezone=timezone_obj,
            )
            domain_obj.reminders.add(reminder_obj)
            reminder_ids.append(reminder_obj.id)
            # for each reminder, schedule sending
            consumer.send_reminder.schedule(
                args=(domain_obj, reminder_obj), eta=reminder_obj.remind_at
            )
        # send welcome email
        consumer.send_welcome_email(email, domain_obj)
        created_data["reminders"] = reminder_ids
    return created_data


def delete_reminder(domain_id: str, reminder_id: int):
    try:
        domain_obj: Domain = Domain.objects.get(domain_unique_id=domain_id)
        reminder_obj: Reminder = Reminder.objects.get(id=reminder_id)
        if not reminder_obj.domain_set.get().id == domain_obj.id:
            raise APIError(message="domain and reminder id not matching")
        with transaction.atomic():
            domain_obj.reminders.remove(reminder_obj)
            reminder_obj.delete()
        # TODO if there are no other reminders associated with this Domain,delete the domain too

    except ObjectDoesNotExist as exception:
        raise APIError(message="reminder not found")


def delete_account(domain_unique_id: str):
    try:
        domain_obj: Domain = Domain.objects.get(domain_unique_id=domain_unique_id)
        reminders: QuerySet = domain_obj.reminders.all()
        with transaction.atomic():
            for reminder in reminders:
                domain_obj.reminders.remove(reminder)
                reminder.delete()
            domain_obj.delete()

    except ObjectDoesNotExist as exception:
        raise APIError(message="Account not found", status=400)
