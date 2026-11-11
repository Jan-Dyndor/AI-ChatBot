from datetime import datetime
from pathlib import Path


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
            message=f"Database operation to update User's {user_id} file {file_name} failed.",
            status_code=500,
            client_message="Database operation to save file failed. Upload file again.",
        )


class FileToLarge(AppExceptions):
    def __init__(self, file_name: str, user_id: int, max_size: int) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_name} is too large. It exceeds {max_size} MB limit",
            status_code=400,
            client_message=f"Given file is to large. It exceeds current {max_size} MB limit",
        )


class FailedFileCleanUp(AppExceptions):
    def __init__(self, file_path: Path, file_id: int, user_id: int) -> None:

        super().__init__(
            message=f"Cound not cleanup after failed file save in storage. Operation is aborted. DB will store file metadata and tried to ad DELETE status attached to file.  !! Manually delete file ID {file_id} in --- {file_path} --- belongs to user {user_id}!!",
            status_code=500,
            client_message="Issue occured while saving the file",
        )


class FailedFileDelete(AppExceptions):
    def __init__(self, file_id: int, user_id: int) -> None:
        super().__init__(
            message=f"Failed to delte User's {user_id} file {file_id} from storage. Whole delete operatin is stopped.",
            status_code=500,
            client_message="Failed to delete the file",
        )


class DatabaseNoRetryError(AppExceptions):
    def __init__(self) -> None:
        super().__init__(
            message="Database operation failed with a non-retryable error",
            status_code=500,
            client_message="Database operation failed. Could not save file metadata.",
        )


class FileAlreadyExists(AppExceptions):
    def __init__(self, file_name: str, user_id: int) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_name} already exists in DB",
            status_code=409,
            client_message=f"File {file_name} already exists. Check indexing process on page 'files page'",
        )


class UploadAfterFailedFileDelation(AppExceptions):
    def __init__(self, file_name: str, user_id: int) -> None:
        super().__init__(
            message=f"User {user_id} attempted to re-upload file {file_name}, but the previous failed upload was not cleaned up successfully. Proceed with manual cleanup. Check File path in DB, delte it from storage and then from DB.",
            status_code=500,
            client_message=f"This file {file_name} could not be uploaded because a previous failed upload was not fully cleaned up. Please contact support.",
        )


class FileIntegrityError(AppExceptions):
    def __init__(self, user_id: int, file_name: str) -> None:
        super().__init__(
            message=f"Integrity issue occurred while tring to safe User's {user_id} file {file_name} spot in DB",
            status_code=500,
            client_message=f"Issue occured while saving the file {file_name} in DB",
        )


class SHACalcuationError(AppExceptions):
    def __init__(self, user_id: int, file_name: str) -> None:
        super().__init__(
            message=f"Issue occured while calculating SHA of user's ID's {user_id} file {file_name}",
            status_code=500,
            client_message="An Issue occured while compering existing files",
        )


class FileStorageException(AppExceptions):
    def __init__(self, user_id: int, file_id: int, file_name: str) -> None:
        super().__init__(
            message=f"Issue occured in creation of storage for file {file_id} from User {user_id}",
            status_code=500,
            client_message=f"Isse occured while saving the file {file_name}",
        )


class FileCanNotBeViewed(AppExceptions):
    def __init__(
        self, user_id: int, file_id: int, file_status: str, file_name: str
    ) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_id} cannot be viewed while its status is {file_status}.",
            status_code=409,
            client_message=f"File {file_name} cannot be viewed. Its due to the file  status: {file_status}.",
        )


class FileNotFoundInStorage(AppExceptions):
    def __init__(
        self,
        user_id: int,
        file_id: int,
    ) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_id} is not present in storage. This validates the Posgtress DB as source of truth rule.",
            status_code=500,
            client_message="Can not view the file, its not in storage.",
        )


class ChromaDBError(AppExceptions):
    def __init__(self, user_id: int, file_id: int) -> None:
        super().__init__(
            message=f"Issue occured while deleting User's {user_id} file {file_id} from ChromaDB",
            status_code=500,
            client_message="Issue occured while delting file for Vector Database",
        )


class FileInDeletionProcess(AppExceptions):
    def __init__(self, user_id: int, file_id: int, index_status: str) -> None:
        super().__init__(
            message=f"User's {user_id} file {file_id} already in deletion process. Index status is {index_status}",
            status_code=409,
            client_message="File is alredy beeing delted",
        )


class FileStillUploading(AppExceptions):
    def __init__(
        self,
        user_id: int,
        file_id: int,
        updated_at: datetime,
        index_status: str,
        file_status: str,
    ) -> None:
        super().__init__(
            message=f"User's {user_id} tring to delete file {file_id} that is still processing. File status: {file_status} and indexing status is {index_status}. File was last time updated at {updated_at}",
            status_code=405,
            client_message="Can not delete file while its still processing the upload. Wait untill file will be stored and indexed in Vector DB",
        )


#! AUTH HTTP validation
class ValidationErrorCredentials(AppExceptions):
    def __init__(self, variable_name, issue_message: str) -> None:
        super().__init__(
            message=f"Input data validation failed {variable_name} -> {issue_message}",
            status_code=422,
            client_message=f"Input data validation failed. {variable_name} -> {issue_message}",
        )
