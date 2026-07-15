# readers/base.py

from abc import ABC, abstractmethod

class BaseReader(ABC):

    extensions = []

    @abstractmethod
    def read(self, filename: str, contents: bytes) -> str:
        pass