from io import BytesIO
import pandas as pd

from .base import BaseReader


class OdsReader(BaseReader):

    extensions = ["ods"]

    def read(self, filename, contents):

        excel = pd.ExcelFile(BytesIO(contents), engine="odf")

        output = []

        for sheet in excel.sheet_names:

            df = excel.parse(sheet)

            output.append(f"===== {sheet} =====")
            output.append(df.to_string(index=False))

        return "\n\n".join(output)