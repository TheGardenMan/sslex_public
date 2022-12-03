# pylint: skip-file
class APIError(Exception):
    def __init__(self, message: str = "Error", status: int = 400) -> None:
        self.message = message
        self.status = status


class HTMLError(Exception):
    def __init__(self, message: str = "Error", status: int = 400) -> None:
        self.message = message
        self.status = status
