"""Exceptions used by the Streamlit frontend to handle chat failures."""


class FrontendExceptions(Exception):
    """Base exception carrying a technical message for logs and debugging."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ChatStreamError(FrontendExceptions):
    """Raised when the backend sends an SSE error event during a chat response."""


class PydanticValidationError(FrontendExceptions):
    """Raised when the backend rejects the request because its data is invalid."""


class DBError(FrontendExceptions):
    """Raised when a requested conversation or related database data is unavailable."""


class InvalidCredentials(FrontendExceptions):
    """Raised when the access token is missing, expired, or invalid."""


class OllamaConnectionError(FrontendExceptions):
    """Raised when the backend cannot connect to the Ollama service."""


class ConversaionInUse(FrontendExceptions):
    """Raised when another request is already being processed for a conversation."""

    def __init__(self, message: str, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(message)


class UnknownError(FrontendExceptions):
    """Raised for an unexpected backend HTTP error not handled specifically."""

    def __init__(self, message: str, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(message)


class NetworkError(FrontendExceptions):
    """Raised when the frontend cannot reach the backend or a request is interrupted."""

    def __init__(self, message: str, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(message)
