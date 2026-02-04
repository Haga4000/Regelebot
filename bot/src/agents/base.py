from abc import ABC, abstractmethod
from typing import Any


class BaseSubAgent(ABC):
    @abstractmethod
    async def execute(self, action: str, **kwargs) -> Any:
        pass
