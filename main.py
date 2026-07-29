from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from readers.text_reader import TextReader
from readers.code_reader import CodeReader
from readers.csv_reader import CsvReader
from readers.json_reader import JsonReader
from readers.word_reader import WordReader
from readers.pdf_reader import PdfReader

from readers.xml_reader import XmlReader

from readers.rtf_reader import RtfReader
from readers.odt_reader import OdtReader

from readers.epub_reader import EpubReader
from readers.excel_reader import ExcelReader
from readers.ods_reader import OdsReader
from readers.odp_reader import OdpReader
from readers.pptx_reader import PptxReader

import yaml
from config_loader import load_yaml
from model_factory import build_models, metadata
from database import engine, SessionLocal
from sqlalchemy import insert, select, delete, update

config = load_yaml()

metadata = build_models(config)

metadata.create_all(engine)


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
    XmlReader(),
    RtfReader(),
    OdtReader(),
    EpubReader(),
    ExcelReader(),
    OdsReader(),
    OdpReader(),
    PptxReader(),
]



@app.get("/api/config")
def get_config():
    with open("config/app.yaml") as f:
        return yaml.safe_load(f)



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


@app.post("/api/{table}")
def create_record(table: str, data: dict):

    db = SessionLocal()

    t = metadata.tables[table]

    db.execute(

        insert(t).values(**data)

    )

    db.commit()

    return {"status": "ok"}

@app.get("/api/{table}")
def list_records(table: str):

    db = SessionLocal()

    t = metadata.tables[table]

    result = db.execute(
        select(t)
    )

    rows = []

    for row in result.mappings():
        rows.append(dict(row))

    db.close()

    return rows

@app.delete("/api/{table}/{id}")
def delete_record(table: str, id: int):

    db = SessionLocal()

    t = metadata.tables[table]

    db.execute(
        delete(t).where(t.c.id == id)
    )

    db.commit()
    db.close()

    return {"status": "deleted"}


@app.put("/api/{table}/{id}")
def update_record(table: str, id: int, data: dict):

    db = SessionLocal()

    t = metadata.tables[table]

    # Never update the primary key
    data.pop("id", None)

    db.execute(
        update(t)
        .where(t.c.id == id)
        .values(**data)
    )

    db.commit()
    db.close()

    return {"status": "updated"}


@app.get("/")
def root():
    return {"status": "OK"}






  
