from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import transaction
from django.db.models.query import QuerySet
from huey.contrib.djhuey import task

from App.models import Domain, Reminder


def send_reminder(domain_obj: Domain, reminder_obj: Reminder):
    user_email: str = reminder_obj.email
    email_text: str = (
        "SSL certificate for "
        + domain_obj.domain_name
        + " is expiring soon.\n"
    )

    remaining_unsent_reminder: QuerySet = domain_obj.reminders.filter(
        is_sent=False
    ).exclude(id=reminder_obj.id)
    if remaining_unsent_reminder.exists():
        email_text = email_text + "You will receive following reminders.\n"
    else:
        email_text = email_text + "This is the last reminder.\n"
        # print("===================================================================")

    for reminder in remaining_unsent_reminder:
        remind_at: datetime = reminder.remind_at
        remind_at_in_user_timezone: datetime = remind_at.astimezone(
            ZoneInfo(reminder.timezone.name)
        )
        # https://www.strfti.me/?f=%25dth+%25B+%25Y+%25I%3A%25M+%25p
        # 09th November 2022 07:37 AM
        remind_at_string: str = "On " + remind_at_in_user_timezone.strftime(
            "%dth %B %Y %I:%M %p"
        )
        reminder_delete_link = (
            settings.BASE_URL
            + "/reminder/"
            + str(domain_obj.domain_unique_id)
            + "/"
            + str(reminder.id)
        )

        email_text = (
            email_text + remind_at_string + "\n" + reminder_delete_link
        )
    account_delete_link = (
        settings.BASE_URL + "/account/" + str(domain_obj.domain_unique_id)
    )
    email_text = email_text + "\n" + account_delete_link
    print(email_text)
    # NEXT
    # implement above variables into template and send email

    # mark this reminder as sent and update sent_at
    with transaction.atomic():
        reminder_obj.is_sent = True
        reminder_obj.sent_at = datetime.utcnow()
        reminder_obj.save()


def send_welcome_email(email: str, domain_obj: Domain):
    reminders: QuerySet = domain_obj.reminders.all()
    email_content = "You will receive reminders in following times.\n"
    domain_name: str = domain_obj.domain_name
    for reminder in reminders:
        remind_at: datetime = reminder.remind_at
        remind_at_in_user_timezone: datetime = remind_at.astimezone(
            ZoneInfo(reminder.timezone.name)
        )
        # https://www.strfti.me/?f=%25dth+%25B+%25Y+%25I%3A%25M+%25p
        # 09th November 2022 07:37 AM
        remind_at_string: str = "On " + remind_at_in_user_timezone.strftime(
            "%dth %B %Y %I:%M %p"
        )
        reminder_delete_link = (
            settings.BASE_URL
            + "/reminder/"
            + str(domain_obj.domain_unique_id)
            + "/"
            + str(reminder.id)
        )
        email_content = (
            email_content
            + remind_at_string
            + "\t --> Delete reminder"
            + reminder_delete_link
        )
        print(reminder_delete_link)
    account_delete_link = (
        settings.BASE_URL + "/account/" + str(domain_obj.domain_unique_id)
    )
    print(account_delete_link)
    email_content = (
        email_content + "Delete all reminders -->" + account_delete_link
    )
    # print(email_content)
    # NEXT
    # implement above variables into template and send email
    """SSL expiry reminder has been created for google.com.
    You will receive a notification on following days (there will be 1 or 2 reminders)
    On 29th June 2022 9AM IST  - Click to delete
    On 19th June 2022 9AM IST -  Click to delete
    Click to delete your email and reminders from our database"""
    # and mark domain_obj.welcome_email_sent as False and save
    pass
