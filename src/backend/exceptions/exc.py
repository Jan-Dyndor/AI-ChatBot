class AppExceptions(Exception):
    def __init__(self, message, status_code) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


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
