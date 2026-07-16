from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from readers.text_reader import TextReader
from readers.code_reader import CodeReader
from readers.csv_reader import CsvReader
from readers.json_reader import JsonReader
from readers.word_reader import WordReader
from readers.pdf_reader import PdfReader

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://sanjeevdg.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

'''
def parse_file(filename: str, contents: bytes):

    try:
        text = contents.decode("utf-8")
    except Exception:
        text = f"Received {len(contents)} bytes. Parser for this file type is not yet implemented."

    return text
'''




READERS = [
    TextReader(),
    CodeReader(),
    CsvReader(),
    JsonReader(),
    WordReader(),
    PdfReader(),
]

def parse_file(filename, contents):

    ext = filename.split(".")[-1].lower()

    for reader in READERS:
        if ext in reader.extensions:
            return reader.read(filename, contents)

    return f"No parser for .{ext}"


@app.post("/api/read-file")
async def read_file(file: UploadFile = File(...)):

    contents = await file.read()

    text = parse_file(file.filename, contents)

    return {
        "success": True,
        "filename": file.filename,
        "type": file.content_type,
        "size": len(contents),
        "text": text,
    }  


@app.get("/")
def root():
    return {"status": "OK"}






  
