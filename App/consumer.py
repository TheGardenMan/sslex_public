from datetime import datetime
from zoneinfo import ZoneInfo

from huey.contrib.djhuey import task

from App import emailer, logic
from App.models import Domain, Reminder


@task()
def send_reminder(
    domain_obj: Domain,
    reminder_obj: Reminder,
):
    """
    Send reminder to given Domain.
    Called by scheduler
    """
    # Domain itself was deleted
    if not Domain.objects.filter(id=domain_obj.id).exists():
        return

    # This particular reminder was deleted
    if not Reminder.objects.filter(id=reminder_obj.id).exists():
        return

    try:
        expiry_datetime: datetime = logic.check_ssl_expiry_date(domain_obj.domain_name)
        if expiry_datetime > datetime.utcnow().astimezone(ZoneInfo("UTC")):
            emailer.send_reminder(domain_obj, reminder_obj)
            # # expiry date hasn't changed
            # if expiry_datetime == reminder_obj.remind_at:
            #     emailer.send_reminder(domain_obj, reminder_obj)
            # # expiry date has increased. User has probably renewed the certificate
            # elif expiry_datetime > reminder_obj.remind_at:
            #     # TODO send congrats mail for renewing the certificate before expiry maybe?
            #     pass
    # exception while checking for SSL - site is unreachable etc. What to do in that case?
    except Exception as e:
        pass


@task()
def send_welcome_email(email: str, domain_obj: Domain):
    emailer.send_welcome_email(email, domain_obj)
