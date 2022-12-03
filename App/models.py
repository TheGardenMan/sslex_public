from uuid import uuid4

from django.db import models


# each reminder is independant. Has its own email field. If we store email in
# domain table, then we will have to change later if someone enters
# the same domain
class Reminder(models.Model):
    email = models.EmailField()
    # in usertimezone
    expiry_date = models.DateTimeField()
    # in UTC
    created_at = models.DateTimeField(auto_now_add=True)
    remind_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True)
    is_sent = models.BooleanField(default=False)
    # timezone of user - will be needed in email to convert UTC time back to user time for showing it to them
    timezone = models.ForeignKey("Timezone", on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return str(self.id) + "-->" + self.email


# each request to create reminders creates a new domain entry.
# Because there's no concept of User.
class Domain(models.Model):
    domain_name = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    # security field. Used in delete reminder or delete data links in emails
    domain_unique_id = models.UUIDField(default=uuid4, db_index=True, unique=True)
    # Stringify the JSON request body and store here
    request_body = models.TextField()
    welcome_email_sent = models.BooleanField(default=False)
    # should be able to find a domain's reminders.
    # A domain may have more than one reminder.
    # M2M field makes it easy
    reminders = models.ManyToManyField(Reminder)

    def __str__(self) -> str:
        return str(self.id) + "-->" + self.domain_name


# Just storing the timezone from which the request was created
class Timezone(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class DummyDomain(models.Model):
    domain_name = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.domain_name
