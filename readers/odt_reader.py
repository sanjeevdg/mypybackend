from io import BytesIO

from odf.opendocument import load
from odf import text

from .base import BaseReader


class OdtReader(BaseReader):

    extensions = ["odt"]

    def read(self, filename, contents):

        doc = load(BytesIO(contents))

        paragraphs = []

        for p in doc.getElementsByType(text.P):
            paragraphs.append("".join(node.data for node in p.childNodes if hasattr(node, "data")))

        return "\n".join(paragraphs)