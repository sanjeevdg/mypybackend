from io import BytesIO

from odf.opendocument import load
from odf.draw import Page
from odf import text

from .base import BaseReader


class OdpReader(BaseReader):

    extensions = ["odp"]

    def read(self, filename, contents):

        doc = load(BytesIO(contents))

        output = []

        for i, page in enumerate(doc.getElementsByType(Page), 1):

            output.append(f"===== Slide {i} =====")

            for p in page.getElementsByType(text.P):
                output.append(
                    "".join(node.data for node in p.childNodes if hasattr(node, "data"))
                )

        return "\n".join(output)