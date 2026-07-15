# readers/csv_reader.py

import pandas as pd
from io import BytesIO

from .base import BaseReader


class CsvReader(BaseReader):

    extensions = ["csv"]

    def read(self, filename, contents):

        df = pd.read_csv(BytesIO(contents))

        return df.to_string()