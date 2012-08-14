class InvalidProblem(Exception):

    def __init__(self, message=None):
        super(InvalidProblem, self).__init__(message)

class UnavailableSource(Exception):

    def __init__(self, message=None):
        super(UnavailableSource, self).__init__(message)
