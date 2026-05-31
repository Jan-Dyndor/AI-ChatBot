# App Error
class AppExceptions(Exception):
    def __init__(self, message, status_code) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Ollama Errors
class OllamaError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(message="Ollama clent encountered error", status_code=500)


class OllamaConnectionError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(message="Could not connect to Ollama", status_code=502)


class OllamaModelError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Ollama model does not exists on that machine or at all",
            status_code=404,
        )


class OllamaConnectionStoppedError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Ollama stopped responding and is unavailable", status_code=500
        )


# DataBase exceptions
class ConversationNotFound(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Conversation with that ID does not yet stores data",
            status_code=200,
        )


class DataBaseError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(message="Database operation failed", status_code=500)


class DataBaseResourceNotFound(AppExceptions):
    def __init__(
        self,
    ):
        super().__init__(
            message="Database cound not find given resource", status_code=404
        )


class UserNotFound(AppExceptions):
    def __init__(self, user_id) -> None:
        super().__init__(
            message=f"User with ID {user_id} not found in DB", status_code=404
        )


class UserAlreadyExists(AppExceptions):
    def __init__(self) -> None:
        super().__init__(message="User with this email already exists", status_code=409)
