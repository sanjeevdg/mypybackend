from fastapi import FastAPI, UploadFile, File, HTTPException
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
from sqlalchemy import insert, select, delete, update, create_engine


from pathlib import Path
import uuid

from database import metadata, engine
from model_factory import build_models
from pathlib import Path


CONFIG_DIR = Path("config")

from dotenv import load_dotenv
import os

load_dotenv()

#DATABASE_URL = os.getenv("DATABASE_URL")






def rebuild_schema():

    metadata.clear()

    config = load_yaml()

    build_models(config)

    metadata.drop_all(bind=engine)

    metadata.create_all(bind=engine)


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

def load_schema():

    metadata.clear()

    config = load_yaml()

    build_models(config)


@app.on_event("startup")
def startup():

    load_schema()    

    print("Loaded tables:")
    print(list(metadata.tables.keys()))


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
def get_config(name: str = "app"):

    config_file = CONFIG_DIR / f"{name}.yaml"

    if not config_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Configuration '{name}.yaml' not found"
        )

    with open(config_file, "r") as f:
        return yaml.safe_load(f)



def parse_file(filename, contents):

    ext = filename.split(".")[-1].lower()

    for reader in READERS:
        if ext in reader.extensions:
            return reader.read(filename, contents)

    return f"No parser for .{ext}"

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):

    ext = Path(file.filename).suffix

    filename = f"{uuid.uuid4()}{ext}"

    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(await file.read())

    return {
        "filename": filename,
        "original": file.filename
    }






@app.post("/api/login")
def login(data: dict):

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Email and password are required"
        )

    db = SessionLocal()

    try:

        t = metadata.tables.get("users")

        if t is None:
            raise HTTPException(
                status_code=500,
                detail="Users table is not loaded"
            )

        result = db.execute(
            select(t).where(
                t.c.email == email
            )
        )

        user = result.mappings().first()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if user["password"] != password:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {
            "status": "ok",
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name")
            }
        }

    finally:
        db.close()




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

def rebuild_schema():

    metadata.clear()

    config = load_yaml()

    build_models(config)

    metadata.drop_all(bind=engine)

    metadata.create_all(bind=engine)

@app.post("/api/admin/recreate/users")
def recreate():

    rebuild_schema()

    return {"status": "ok"}




def get_table(table_name):

    if table_name not in metadata.tables:

        metadata.clear()

        config = load_yaml()

        build_models(config)

    return metadata.tables[table_name]





@app.delete("/api/admin/table/{table}")
def drop_table(table: str):

    db = SessionLocal()

    try:

        t = metadata.tables.get(table)

        if t is None:
            raise HTTPException(status_code=404, detail="Table not found")

        t.drop(bind=engine, checkfirst=True)

        return {"status": "ok", "table": table}

    finally:
        db.close()

@app.post("/api/{table}")
def create_record(table: str, data: dict):

    db = SessionLocal()

    t = get_table(table)

    db.execute(insert(t).values(**data))

    db.commit()
    db.close()

    return {"status": "ok"}

@app.get("/api/{table}")
def list_records(table: str):

    db = SessionLocal()

    try:

        t = metadata.tables[table]

        columns = [
            c for c in t.c
            if c.name != "password"
        ]

        result = db.execute(
            select(*columns)
        )

        return [
            dict(row)
            for row in result.mappings()
        ]

    finally:
        db.close()

@app.delete("/api/{table}/{id}")
def delete_record(table: str, id: int):

    db = SessionLocal()

    t = get_table(table)

    db.execute(
        delete(t).where(t.c.id == id)
    )

    db.commit()
    db.close()

    return {"status": "deleted"}


@app.put("/api/{table}/{id}")
def update_record(table: str, id: int, data: dict):

    db = SessionLocal()

    t = get_table(table)

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






  
