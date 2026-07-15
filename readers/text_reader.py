# readers/text_reader.py

from .base import BaseReader


class TextReader(BaseReader):

    extensions = [
        "txt",
        "md",
        "log"
    ]

    def read(self, filename, contents):

        try:
            return contents.decode("utf-8")
        except:
            return contents.decode(errors="ignore")