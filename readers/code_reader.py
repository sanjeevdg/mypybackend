# readers/code_reader.py

from .base import BaseReader


class CodeReader(BaseReader):

    extensions = [
        "py",
        "js",
        "ts",
        "tsx",
        "jsx",
        "java",
        "cpp",
        "c",
        "cs",
        "go",
        "rs",
        "php",
        "rb",
        "swift",
        "kt"
    ]

    def read(self, filename, contents):

        return contents.decode(errors="ignore")