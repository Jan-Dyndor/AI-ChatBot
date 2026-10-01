# App Error
class AppExceptions(Exception):
    def __init__(self, message: str, status_code: int, client_message: str) -> None:
        self.message = message
        self.status_code = status_code
        self.client_message = client_message
        super().__init__(message)


# Ollama Errors
class OllamaError(AppExceptions):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            message="Ollama clent encountered error",
            status_code=500,
            client_message="Ollama clent encountered error",
        )


class OllamaConnectionError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Could not connect to Ollama",
            status_code=502,
            client_message="Could not connect to Ollama",
        )


class OllamaModelError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Ollama model does not exists on that machine or at all",
            status_code=404,
            client_message="Ollama model does not exists on that machine or at all",
        )


class OllamaEmbeddingModelError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Ollama Embedding Models can not generate responses",
            status_code=400,
            client_message="Ollama Embedding Models can not generate responses",
        )


class OllamaConnectionStoppedError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Ollama stopped responding and is unavailable",
            status_code=500,
            client_message="Ollama stopped responding and is unavailable",
        )


# DataBase exceptions
class ConversationNotFound(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Conversation with that ID does not yet stores data",
            status_code=200,
            client_message="Conversation with that ID does not yet stores data",
        )


class DataBaseError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Database operation failed",
            status_code=500,
            client_message="Database operation failed",
        )


class DataBaseResourceNotFound(AppExceptions):
    def __init__(
        self,
    ):
        super().__init__(
            message="Database cound not find given resource",
            status_code=404,
            client_message="Database cound not find given resource",
        )


class UserNotFound(AppExceptions):
    def __init__(self, user_id) -> None:
        super().__init__(
            message=f"User with ID {user_id} not found in DB",
            status_code=404,
            client_message=f"User with ID {user_id} not found in DB",
        )


class UserAlreadyExists(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="User with this email already exists",
            status_code=409,
            client_message="User with this email already exists",
        )


class InvalidCredentials(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Could not validate credentials",
            status_code=401,
            client_message="Could not validate credentials",
        )


# Concurency exception


class ConversationIDConflict(AppExceptions):
    def __init__(self, conversation_id) -> None:
        super().__init__(
            message=f"Conversation {conversation_id} already processing",
            status_code=409,
            client_message=f"Conversation {conversation_id} already processing",
        )


# File exception
class FileNotSaved(AppExceptions):
    def __init__(self, file_name, user_id, file_path) -> None:
        super().__init__(
            message=f"Issue with saving file {file_name} from user {user_id} to its destination in {file_path}",
            status_code=500,
            client_message=f"Issue with saving file {file_name}",
        )


class NotEnoughtFileParameters(AppExceptions):
    def __init__(self, user_id: int, file_param: str) -> None:
        super().__init__(
            message=f"Can not process user's {user_id} file. There is no {file_param} attribute ",
            status_code=400,
            client_message="Invalid file. Can not upload.",
        )


class DataBaseFileError(AppExceptions):
    def __init__(self, user_id: int, file_name: str) -> None:
        super().__init__(
            message=f"Database operation to save user's {user_id} file {file_name} failed. File is being deleted from storage.",
            status_code=500,
            client_message="Database operation failed. File is deleted. Upload file again.",
        )


class FileToLarge(AppExceptions):
    def __init__(self, file_name: str, user_id: int, max_size: int) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_name} is too large. It exceeds {max_size} MB limit",
            status_code=400,
            client_message=f"Given file is to large. It exceeds current {max_size} MB limit",
        )
