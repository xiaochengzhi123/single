class SignalTutorError(Exception):
    """Base domain error."""


class ProblemParseError(SignalTutorError):
    pass


class LowConfidenceVisionError(SignalTutorError):
    pass


class AmbiguousProblemError(SignalTutorError):
    pass


class MathToolError(SignalTutorError):
    pass


class VerificationError(SignalTutorError):
    pass


class RetrievalError(SignalTutorError):
    pass
