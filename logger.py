import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ArbitrageError(Exception):
    def __init__(self, message: str, line_number: int = None, filename: str = None):
        self.message = message
        self.line_number = line_number
        self.filename = filename
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.line_number and self.filename:
            return f"{self.message} (line {self.line_number} in {self.filename})"
        return self.message


class ErrorLogger:
    def __init__(self, name: str = "arbitrage_finder"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.ERROR)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - ERROR - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_error(
        self,
        error: Exception,
        context: str = "",
        include_traceback: bool = True,
    ) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb = traceback.extract_tb(error.__traceback__)

        if tb:
            last_frame = tb[-1]
            line_num = last_frame.lineno
            filename = last_frame.filename
            func_name = last_frame.name

            error_msg = f"[{timestamp}] Error in {func_name}()"
            if context:
                error_msg += f" - {context}"
            error_msg += f"\n  File: {filename}"
            error_msg += f"\n  Line: {line_num}"
            error_msg += f"\n  Error: {type(error).__name__}: {error}"

            if include_traceback and error.__traceback__:
                tb_str = "".join(traceback.format_tb(error.__traceback__))
                error_msg += f"\n  Traceback:\n{tb_str}"

            self.logger.error(error_msg)
        else:
            error_msg = f"[{timestamp}] Error: {type(error).__name__}: {error}"
            if context:
                error_msg += f" - {context}"
            self.logger.error(error_msg)

    def log_with_context(self, context: str = ""):
        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.log_error(e, context=context or f"in {func.__name__}()")
                    raise

            return wrapper

        return decorator


error_logger = ErrorLogger()

