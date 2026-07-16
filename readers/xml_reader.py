import xml.etree.ElementTree as ET
from io import BytesIO

from .base import BaseReader


class XmlReader(BaseReader):

    extensions = ["xml"]

    def read(self, filename, contents):

        tree = ET.parse(BytesIO(contents))
        root = tree.getroot()

        text = []

        for elem in root.iter():
            if elem.text:
                text.append(elem.text.strip())

        return "\n".join(filter(None, text))