

class RequestsError(Exception):
    """
    Raised when trying to access a url
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
