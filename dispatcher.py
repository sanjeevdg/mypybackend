# dispatcher.py

from readers.text_reader import TextReader
from readers.code_reader import CodeReader
from readers.csv_reader import CsvReader
from readers.json_reader import JsonReader
from readers.word_reader import WordReader


READERS = [
    TextReader(),
    CodeReader(),
    CsvReader(),
    JsonReader(),
    WordReader(),
]


def parse_file(filename, contents):

    ext = filename.split(".")[-1].lower()

    for reader in READERS:

        if ext in reader.extensions:
            return reader.read(filename, contents)

    return f"No reader installed for *.{ext}"