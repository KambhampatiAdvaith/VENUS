import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)


def configure_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format=DEFAULT_LOG_FORMAT,
        )

    backend_logger = logging.getLogger("backend")

    if backend_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    backend_logger.addHandler(handler)
    backend_logger.setLevel(level)
    backend_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


@dataclass
class BackoffState:
    initial_delay: float = 1.0
    max_delay: float = 30.0
    factor: float = 2.0
    jitter: float = 0.0
    attempt: int = 0

    def next_delay(self) -> float:
        delay = min(
            self.max_delay,
            self.initial_delay * (self.factor ** self.attempt),
        )
        self.attempt += 1

        if self.jitter > 0:
            delay += random.uniform(0, self.jitter)

        return delay

    def reset(self) -> None:
        self.attempt = 0


T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    *,
    logger: logging.Logger,
    operation_name: str,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: float = 0.0,
    max_attempts: int | None = None,
) -> T:
    backoff = BackoffState(
        initial_delay=initial_delay,
        max_delay=max_delay,
        factor=factor,
        jitter=jitter,
    )
    attempt = 0

    while True:
        try:
            return operation()
        except exceptions as error:
            attempt += 1

            if max_attempts is not None and attempt >= max_attempts:
                logger.exception(
                    "%s failed after %s attempt(s).",
                    operation_name,
                    attempt,
                )
                raise

            delay = backoff.next_delay()
            logger.warning(
                "%s failed on attempt %s: %s. Retrying in %.1f seconds.",
                operation_name,
                attempt,
                error,
                delay,
            )
            time.sleep(delay)
