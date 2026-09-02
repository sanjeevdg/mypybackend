from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Depends, Body
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
from database import engine, SessionLocal, metadata

from sqlalchemy import insert, select, delete, update, create_engine, text
from passlib.context import CryptContext

from pathlib import Path
import uuid

from database import metadata, engine
from model_factory import build_models
from pathlib import Path
from typing import Any

CONFIG_DIR = Path("config")

from dotenv import load_dotenv
import os

load_dotenv()

#DATABASE_URL = os.getenv("DATABASE_URL")


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)



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

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid YAML: {str(e)}"
        )



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



@app.post("/api/change-password")
def change_password(data: dict):

    db = SessionLocal()

    try:

        email = data.get("email")
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        # ---------------------------------------------
        # Validation
        # ---------------------------------------------

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email is required"
            )

        if not current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password is required"
            )

        if not new_password:
            raise HTTPException(
                status_code=400,
                detail="New password is required"
            )

        if len(new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must contain at least 8 characters"
            )

        # ---------------------------------------------
        # Users table
        # ---------------------------------------------

        t = metadata.tables["users"]

        # ---------------------------------------------
        # Find user
        # ---------------------------------------------

        result = db.execute(
            select(t).where(
                t.c.email == email
            )
        )

        user = result.mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # ---------------------------------------------
        # Existing passwords are plain text
        # ---------------------------------------------

        if current_password != user["password"]:
            raise HTTPException(
                status_code=401,
                detail="Current password is incorrect"
            )

        # ---------------------------------------------
        # Hash new password
        # ---------------------------------------------
        print("EMAIL:", email)
        print("CURRENT PASSWORD LENGTH:", len(current_password))
        print("NEW PASSWORD LENGTH:", len(new_password))
        print("NEW PASSWORD BYTES:", len(new_password.encode("utf-8")))

        hashed_password = pwd_context.hash(
            new_password
        )

        # ---------------------------------------------
        # Update password
        # ---------------------------------------------

        db.execute(
            update(t)
            .where(
                t.c.id == user["id"]
            )
            .values(
                password=hashed_password
            )
        )

        db.commit()

        return {
            "success": True,
            "message": "Password changed successfully"
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        print(
            "CHANGE PASSWORD ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()


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

@app.post("/api/admin/recreate")
def recreate():

    rebuild_schema()

    return {"status": "ok"}


@app.post("/api/admin/migrate/orders-amount")
def migrate_orders_amount():

    try:

        with engine.begin() as conn:

            conn.execute(
                text("""
                    ALTER TABLE orders
                    ALTER COLUMN amount TYPE NUMERIC(12,2)
                    USING NULLIF(TRIM(amount), '')::NUMERIC
                """)
            )

        return {
            "success": True,
            "message": "orders.amount converted to NUMERIC(12,2)"
        }

    except Exception as e:

        print("Migration error:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/chart")
def get_chart_data(
    entity: str,
    x: str,
    y: str
):

    # -----------------------------------------
    # ENTITY VALIDATION
    # -----------------------------------------

    if entity not in metadata.tables:

        raise HTTPException(
            status_code=400,
            detail=f"Unknown entity: {entity}"
        )

    table = metadata.tables[entity]

    # -----------------------------------------
    # FIELD VALIDATION
    # -----------------------------------------

    if x not in table.c:

        raise HTTPException(
            status_code=400,
            detail=f"Unknown x field '{x}' in '{entity}'"
        )

    if y not in table.c:

        raise HTTPException(
            status_code=400,
            detail=f"Unknown y field '{y}' in '{entity}'"
        )

    # -----------------------------------------
    # QUERY
    # -----------------------------------------

    sql = text(
        f"""
        SELECT
            {x},
            {y}
        FROM {entity}
        WHERE {x} IS NOT NULL
          AND {y} IS NOT NULL
        ORDER BY {x}
        """
    )

    with engine.connect() as conn:

        rows = conn.execute(sql).mappings().all()

    # -----------------------------------------
    # RETURN CHART DATA
    # -----------------------------------------

    result = []

    for row in rows:

        result.append({
            "x": row[x],
            "y": float(row[y])
        })

    return result

@app.post("/api/stats")
def get_stats(payload: dict[str, Any] = Body(...)):

    stats = payload.get("stats", [])
    selected_customer_id = payload.get("selectedCustomerId")

    selected_customer_id = payload.get("selectedCustomerId")

    print("========== STATS API DEBUG ==========")
    print("selectedCustomerId:", selected_customer_id)
    print("stats:", stats)
    print("=====================================")

    if not isinstance(stats, list):
        raise HTTPException(
            status_code=400,
            detail="'stats' must be a list"
        )

    results = []

    for stat in stats:

        title = stat.get("title", "")
        entity = stat.get("entity")
        field = stat.get("field")
        aggregate = stat.get("aggregate")
        value = stat.get("value")

        # -----------------------------------------
        # BASIC VALIDATION
        # -----------------------------------------

        if not entity:
            raise HTTPException(
                status_code=400,
                detail=f"Stat '{title}' has no entity"
            )

        if not aggregate:
            raise HTTPException(
                status_code=400,
                detail=f"Stat '{title}' has no aggregate"
            )

        # -----------------------------------------
        # ENTITY VALIDATION
        # -----------------------------------------

        if entity not in metadata.tables:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown entity: {entity}"
            )

        table = metadata.tables[entity]

        # -----------------------------------------
        # FIELD VALIDATION
        # -----------------------------------------

        if field is not None and field not in table.c:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown field '{field}' in entity '{entity}'"
            )

        # -----------------------------------------
        # AGGREGATE VALIDATION
        # -----------------------------------------

        allowed_aggregates = {
            "count",
            "sum"
        }

        if aggregate not in allowed_aggregates:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported aggregate: {aggregate}"
            )

        # -----------------------------------------
        # COUNT
        # -----------------------------------------

        if aggregate == "count":

            conditions = []
            params = {}

            # -----------------------------------------
            # YAML VALUE FILTER
            # -----------------------------------------

            if field and value is not None:

                conditions.append(
                    f"{field} = :value"
                )

                params["value"] = value

            # -----------------------------------------
            # SELECTED CUSTOMER FILTER
            # -----------------------------------------

            filter_config = stat.get("filter")

            if filter_config:

                filter_field = filter_config.get("field")

                if filter_field not in table.c:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Unknown filter field "
                            f"'{filter_field}' in entity '{entity}'"
                        )
                    )

                if selected_customer_id is None:
                    result = 0
                else:

                    conditions.append(
                        f"{filter_field} = :selected_customer_id"
                    )

                    params["selected_customer_id"] = (
                        selected_customer_id
                    )

                    where_clause = (
                        " WHERE " +
                        " AND ".join(conditions)
                        if conditions
                        else ""
                    )

                    sql = text(
                        f"""
                        SELECT COUNT(*)
                        FROM {entity}
                        {where_clause}
                        """
                    )

                    with engine.connect() as conn:

                        result = conn.execute(
                            sql,
                            params
                        ).scalar()

            else:

                where_clause = (
                    " WHERE " +
                    " AND ".join(conditions)
                    if conditions
                    else ""
                )

                sql = text(
                    f"""
                    SELECT COUNT(*)
                    FROM {entity}
                    {where_clause}
                    """
                )

                with engine.connect() as conn:

                    result = conn.execute(
                        sql,
                        params
                    ).scalar()

        # -----------------------------------------
        # SUM
        # -----------------------------------------

        elif aggregate == "sum":

            if not field:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stat '{title}' requires a field for sum"
                )

            conditions = []
            params = {}

            filter_config = stat.get("filter")

            if filter_config:

                filter_field = filter_config.get("field")

                if filter_field not in table.c:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Unknown filter field "
                            f"'{filter_field}' in entity '{entity}'"
                        )
                    )

                if selected_customer_id is None:

                    result = 0

                else:

                    conditions.append(
                        f"{filter_field} = :selected_customer_id"
                    )

                    params["selected_customer_id"] = (
                        selected_customer_id
                    )

                    where_clause = (
                        " WHERE " +
                        " AND ".join(conditions)
                    )

                    sql = text(
                        f"""
                        SELECT COALESCE(SUM({field}), 0)
                        FROM {entity}
                        {where_clause}
                        """
                    )

                    with engine.connect() as conn:

                        result = conn.execute(
                            sql,
                            params
                        ).scalar()

            else:

                sql = text(
                    f"""
                    SELECT COALESCE(SUM({field}), 0)
                    FROM {entity}
                    """
                )

                with engine.connect() as conn:

                    result = conn.execute(sql).scalar()

        # -----------------------------------------
        # RESULT
        # -----------------------------------------

        results.append({
            "title": title,
            "value": result if result is not None else 0
        })

    return results


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

    try:

        t = get_table(table)

        # Remove ID when creating a new record.
        # The database should generate it.
        if data.get("id") is None:
            data.pop("id", None)

        result = db.execute(
            insert(t)
            .values(**data)
            .returning(t)
        )

        created = result.fetchone()

        db.commit()

        return dict(created._mapping)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

@app.get("/api/{table}/{record_id}")
def get_record(table: str, record_id: int):

    db = SessionLocal()

    try:

        # Get dynamic SQLAlchemy table
        t = metadata.tables[table]

        # Find the record by primary key
        result = db.execute(
            select(t).where(
                t.c.id == record_id
            )
        )

        row = result.mappings().first()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"{table} record {record_id} not found"
            )

        # Don't return password
        record = {
            key: value
            for key, value in row.items()
            if key != "password"
        }

        return record

    finally:

        db.close()

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






  
