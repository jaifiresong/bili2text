from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DomainException(Exception):
    """领域异常基类"""
    pass


class InvalidVideoUrlError(DomainException):
    pass


class TaskNotFoundError(DomainException):
    pass


class TaskAlreadyProcessingError(DomainException):
    pass
