from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    # if response is None, it means there is a non-API error which can't be caught here
    if response is not None:
        if response.status_code == 400:
            pass
        pass

    return response
