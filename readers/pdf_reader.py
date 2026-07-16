import fitz

from .base import BaseReader


class PdfReader(BaseReader):

    extensions = ["pdf"]

    def read(self, filename, contents):

        doc = fitz.open(stream=contents, filetype="pdf")

        output = []

        try:
            for page_no, page in enumerate(doc, start=1):

                text = page.get_text("text").strip()

                output.append(
                    f"===== PAGE {page_no} =====\n{text}"
                )

        finally:
            doc.close()

        return "\n\n".join(output)