# SSL Expiry checker

A simple site to check SSL expiry date and set email reminders.

Uses Huey queue for sending email reminders.

Run the Huey consumer  `python manage.py run_huey` and run the server 
`python manage.py runserver`

Email client and front-end has not been implemented yet.

There's a minimal front-end page for checking the expiry date at index (`example.com/`).




