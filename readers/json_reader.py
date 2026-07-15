# readers/json_reader.py

import json

from .base import BaseReader


class JsonReader(BaseReader):

    extensions = ["json"]

    def read(self, filename, contents):

        obj = json.loads(contents)

        return json.dumps(
            obj,
            indent=4,
            ensure_ascii=False
        )