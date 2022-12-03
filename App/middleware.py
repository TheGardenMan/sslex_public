import json

from django.shortcuts import HttpResponse, render

from App.errors import APIError, HTMLError


class ErrorHandlerMiddleware:
    # https://www.shubhamdipt.com/blog/django-catch-exceptions-and-custom-error-handling/
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    # https://docs.djangoproject.com/en/4.0/topics/http/middleware/#process-exception
    def process_exception(self, request, exception):
        if isinstance(exception, APIError):
            # You can only return a HttpResponse from here
            return HttpResponse(
                json.dumps({"message": exception.message}),
                content_type="application/json",
                status=exception.status,
            )
        # TODO - can raise and handle an error which requires HTML response
        # if isinstance(exception, HTMLError):
        #     # You can only return a HttpResponse from here
        #     return render(
        #         request,
        #         "error.html",
        #         context={"message": exception.message},
        #         status=exception.status,
        #     )
