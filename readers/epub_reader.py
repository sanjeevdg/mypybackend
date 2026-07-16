from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os

from .base import BaseReader


class EpubReader(BaseReader):

    extensions = ["epub"]

    def read(self, filename, contents):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as f:
            f.write(contents)
            tempname = f.name

        try:
            book = epub.read_epub(tempname)

            output = []

            for item in book.get_items():

                if item.get_type() == 9:      # XHTML document

                    soup = BeautifulSoup(item.get_content(), "html.parser")
                    output.append(soup.get_text())

            return "\n".join(output)

        finally:
            os.remove(tempname)