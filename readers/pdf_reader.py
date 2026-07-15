import fitz

from .base import BaseReader


class PdfReader(BaseReader):

    extensions = ["pdf"]

    def read(self, filename: str, contents: bytes) -> str:

        text = []

        pdf = fitz.open(stream=contents, filetype="pdf")

        try:
            for page in pdf:
                page_text = page.get_text("text")

                if page_text:
                    text.append(page_text)

        finally:
            pdf.close()

        return "\n\n".join(text)