from striprtf.striprtf import rtf_to_text

from .base import BaseReader


class RtfReader(BaseReader):

    extensions = ["rtf"]

    def read(self, filename, contents):

        return rtf_to_text(contents.decode("utf-8", errors="ignore"))