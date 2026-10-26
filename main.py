from fastapi import FastAPI, UploadFile, File, HTTPException, Request, APIRouter, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
import cloudinary.uploader


import smtplib

from email.message import EmailMessage

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

from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field
import yaml

from config_loader import load_yaml
from model_factory import build_models, metadata
from database import engine, SessionLocal, metadata

from sqlalchemy import insert, select, delete, update, create_engine, text, func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from pathlib import Path
import uuid
from datetime import date
from database import metadata, engine
from pathlib import Path
from typing import Any

CONFIG_DIR = Path("config")

from dotenv import load_dotenv
import os
from auth import auth_users, create_auth_table
from auth_security import (
    create_access_token,
    get_current_user,
    require_admin
)

from config_loader import load_yaml, load_shared_yaml, deep_merge

load_dotenv()

#DATABASE_URL = os.getenv("DATABASE_URL")

app_config = {}

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

class SaveConfigRequest(BaseModel):
    name: str
    config: dict






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
    global app_config

    metadata.clear()

    # Load the shared entities and relationships.
    shared_config = load_shared_yaml()

    # Retain the existing customer master-detail page configuration.
    page_config = load_yaml()

    # Combine them, preserving page-specific settings.
    app_config = deep_merge(shared_config, page_config)

    # Build database models using the combined configuration.
    build_models(app_config)


@app.on_event("startup")
def startup():

    load_schema()    

    print("Loaded tables:")
    print(list(metadata.tables.keys()))
    customers = metadata.tables["customers"]


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




@app.get("/api/me")
def get_my_account(
    current_user: dict = Depends(get_current_user)
):
    return {
        "status": "ok",
        "user": current_user
    }



@app.get("/api/config")
def get_config(name: str = "app"):

    config_file = CONFIG_DIR / f"{name}.yaml"

    if not config_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Configuration '{name}.yaml' not found"
        )

    try:
        with config_file.open("r", encoding="utf-8") as f:
            page_config = yaml.safe_load(f) or {}

        shared_config = load_shared_yaml()

        # Shared settings are defaults; page settings take precedence.
        config = deep_merge(shared_config, page_config)

        return config

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









class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)


@app.post("/api/signup", status_code=201)
def signup(data: SignupRequest):
    email = str(data.email).strip().lower()
    password = data.password

    # bcrypt has a 72-byte password limit.
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must be no more than 72 bytes."
        )

    with SessionLocal() as db:
        existing = db.execute(
            select(auth_users.c.id).where(
                auth_users.c.email == email
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists."
            )

        password_hash = pwd_context.hash(password)

        
        try:
            result = db.execute(
                insert(auth_users).values(
                    email=email,
                    password_hash=password_hash,
                    role="user",
                    is_active=True
                ).returning(auth_users.c.id)
            )

            user_id = result.scalar_one()

            # Create the linked customer profile.
            db.execute(
                text("""
                    INSERT INTO customers (
                        user_id,
                        first_name,
                        last_name,
                        email,
                        active
                    )
                    VALUES (
                        :user_id,
                        '',
                        '',
                        :email,
                        TRUE
                    )
                """),
                {
                    "user_id": user_id,
                    "email": email
                }
            )

            # Both records are committed together.
            db.commit()

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists."
            )


        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists."
            )

    return {
        "status": "ok",
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "email": email,
            "role": "user"
        }
    }








class ProfileUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = None
    city: str | None = None


@app.get("/api/profile")
def get_profile(
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("id")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    with SessionLocal() as db:
        customers = metadata.tables["customers"]
        result = db.execute(
            select(customers).where(
                customers.c.user_id == user_id
            )
        )
        profile = result.mappings().first()

        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        return dict(profile)


@app.put("/api/profile")
def update_profile(
    data: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("id")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    email = str(data.email).strip().lower()
    first_name = data.first_name.strip()
    last_name = data.last_name.strip()

    if not first_name or not last_name:
        raise HTTPException(
            status_code=422,
            detail="First name and last name cannot be blank"
        )

    if data.gender not in (None, "Male", "Female", "Other"):
        raise HTTPException(status_code=422, detail="Invalid gender")

    if data.city not in (
        None, "London", "Paris", "Delhi",
        "Kolkata", "Mumbai", "Bangalore"
    ):
        raise HTTPException(status_code=422, detail="Invalid city")

    try:
        customers = metadata.tables["customers"]
        with SessionLocal() as db:
            profile = db.execute(
                select(customers.c.id).where(
                    customers.c.user_id == user_id
                )
            ).first()

            if profile is None:
                raise HTTPException(
                    status_code=404,
                    detail="Profile not found"
                )

            # Keep the login email and profile email synchronized.
            db.execute(
                update(auth_users)
                .where(auth_users.c.id == user_id)
                .values(email=email)
            )

            db.execute(
                update(customers)
                .where(customers.c.user_id == user_id)
                .values(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    age=data.age,
                    gender=data.gender,
                    city=data.city
                )
            )

            db.commit()

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="That email address is already in use"
        )

    return {
        "status": "ok",
        "message": "Profile updated successfully"
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

    email = email.strip().lower()

    db = SessionLocal()

    try:
        result = db.execute(
            select(auth_users).where(
                auth_users.c.email == email
            )
        )

        user = result.mappings().first()

        # Use the same generic message for an unknown email
        # and an incorrect password.
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not pwd_context.verify(
            password,
            user["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=403,
                detail="This account is inactive"
            )

        token = create_access_token({
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        })

        return {
            "status": "ok",
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"]
            }
        }

    finally:
        db.close()



@app.post("/api/config/save")
def save_config(request: SaveConfigRequest):

    try:

        # Directory containing YAML configuration files
        config_dir = Path("config")

        # Make sure the directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Prevent accidental directory traversal
        safe_name = Path(
            request.name.strip().strip("'\"")
        ).name

        if not safe_name:
            raise HTTPException(
                status_code=400,
                detail="Configuration name is required"
            )

        # Add .yaml extension if necessary
        if not safe_name.endswith(".yaml"):
            safe_name += ".yaml"

        config_path = config_dir / safe_name

        # Write YAML
        with open(
            config_path,
            "w",
            encoding="utf-8"
        ) as file:

            yaml.safe_dump(
                request.config,
                file,
                sort_keys=False,
                allow_unicode=True
            )

        return {
            "success": True,
            "message": "Configuration saved successfully",
            "name": safe_name,
            "path": str(config_path)
        }

    except HTTPException:
        raise

    except Exception as e:

        print("SAVE CONFIG ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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

    # WARNING: This drops ALL YAML-generated tables and their data.
    metadata.drop_all(bind=engine)

    metadata.create_all(bind=engine)

    # Add the FK and populate profiles after the tables exist.
    with engine.begin() as conn:

        conn.exec_driver_sql("""
            ALTER TABLE customers
            ADD CONSTRAINT fk_customers_auth_users
            FOREIGN KEY (user_id)
            REFERENCES auth_users(id)
            ON DELETE CASCADE
        """)

        # Create a blank customer profile for every existing user.
        conn.exec_driver_sql("""
            INSERT INTO customers (
                user_id,
                first_name,
                last_name,
                email,
                active
            )
            SELECT
                id,
                '',
                '',
                email,
                TRUE
            FROM auth_users
        """)

    print(
        "Schema recreated and customer profiles "
        "created for existing users."
    )

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
    y: str,
    filter_field: str | None = None,
    filter_value: str | None = None
):
    from sqlalchemy import text
    from fastapi import HTTPException
    from datetime import date, datetime
    from decimal import Decimal

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
    # FILTER VALIDATION
    # -----------------------------------------

    if filter_field is not None:
        if filter_field not in table.c:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown filter field "
                    f"'{filter_field}' in '{entity}'"
                )
            )

        if filter_value is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "filter_value is required when "
                    "filter_field is provided"
                )
            )

    # -----------------------------------------
    # QUERY
    # -----------------------------------------

    # Quote identifiers using the active database dialect.
    preparer = engine.dialect.identifier_preparer

    q_entity = preparer.quote(entity)
    q_x = preparer.quote(x)
    q_y = preparer.quote(y)

    sql_string = f"""
        SELECT
            {q_x} AS x_value,
            {q_y} AS y_value
        FROM {q_entity}
        WHERE {q_x} IS NOT NULL
          AND {q_y} IS NOT NULL
    """

    params = {}

    if filter_field is not None:
        q_filter = preparer.quote(filter_field)

        sql_string += f"""
          AND {q_filter} = :filter_value
        """

        params["filter_value"] = filter_value

    sql_string += f"""
        ORDER BY {q_x}
    """

    # -----------------------------------------
    # EXECUTE QUERY
    # -----------------------------------------

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql_string),
            params
        ).mappings().all()

    # -----------------------------------------
    # RETURN CHART DATA
    # -----------------------------------------

    def serialize_value(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return float(value)

        return value

    result = []

    for row in rows:
        x_value = serialize_value(row["x_value"])
        y_value = serialize_value(row["y_value"])

        # Convert Y to a number only when it is numeric.
        # Keep categorical values such as "Draft" as strings.
        if isinstance(y_value, bool):
            pass
        elif isinstance(y_value, (int, float)):
            pass
        else:
            try:
                y_value = float(y_value)
            except (ValueError, TypeError):
                pass

        result.append({
            "x": x_value,
            "y": y_value
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









@app.get("/api/my-orders")
def get_my_orders(
    current_user: dict = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        orders = get_table("orders")
        order_items = get_table("order_items")
        inventory = get_table("inventory")
        customers = get_table("customers")

        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Authenticated user email is unavailable."
            )

        customer = db.execute(
            select(customers).where(
                func.lower(customers.c.email)
                == user_email.strip().lower()
            )
        ).mappings().first()

        if not customer:
            return []

        customer_orders = db.execute(
            select(orders)
            .where(
                orders.c.customer_id == customer["id"]
            )
            .order_by(
                orders.c.order_date.desc(),
                orders.c.id.desc()
            )
        ).mappings().all()

        result = []

        for order in customer_orders:
            order_id = order["id"]

            rows = db.execute(
                select(
                    order_items.c.id,
                    order_items.c.product_id,
                    order_items.c.quantity,
                    order_items.c.amount,
                    inventory.c.name.label("product_name"),
                    inventory.c.sku.label("sku")
                )
                .select_from(
                    order_items.join(
                        inventory,
                        order_items.c.product_id
                        == inventory.c.id
                    )
                )
                .where(
                    order_items.c.order_id == order_id
                )
            ).mappings().all()

            items = []

            for row in rows:
                item = dict(row)
                items.append(item)

            total = sum(
                float(item["amount"] or 0)
                for item in items
            )

            result.append({
                "id": order["id"],
                "order_date": order["order_date"],
                "status": order["status"],
                "total": round(total, 2),
                "items": items
            })

        return result

    except HTTPException:
        raise

    finally:
        db.close()


















@app.post("/api/checkout")
def checkout_order(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        orders = get_table("orders")
        order_items = get_table("order_items")
        inventory = get_table("inventory")
        customers = get_table("customers")

        # Identify the customer using the authenticated user.
        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Authenticated user email is unavailable."
            )

        with db.begin():

            customer = db.execute(
                select(customers).where(
                    func.lower(customers.c.email)
                    == user_email.strip().lower()
                )
            ).mappings().first()

            if not customer:
                raise HTTPException(
                    status_code=400,
                    detail="No customer record is linked to your account."
                )

            cart_items = data.get("items", [])

            if not isinstance(cart_items, list) or not cart_items:
                raise HTTPException(
                    status_code=400,
                    detail="Your shopping cart is empty."
                )

            # Validate the cart and calculate all amounts
            # using prices from the database.
            validated_items = []
            order_total = 0
            email_items = []

            for item in cart_items:
                try:
                    product_id = int(item["id"])
                    quantity = int(item["quantity"])
                except (KeyError, TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid product or quantity."
                    )

                if product_id <= 0 or quantity <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Product IDs and quantities must be positive."
                    )

                product = db.execute(
                    select(inventory)
                    .where(inventory.c.id == product_id)
                    .with_for_update()
                ).mappings().first()

                if not product:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product {product_id} was not found."
                    )

                if (
                    "active" in product
                    and not product["active"]
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product {product_id} is unavailable."
                    )

                price = float(product["price"])
                if price <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product {product_id} has an invalid price."
                    )

                if (
                    "stock_quantity" in product
                    and product["stock_quantity"] is not None
                    and quantity > product["stock_quantity"]
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient stock for product {product_id}."
                    )

                amount = round(price * quantity, 2)
                order_total += amount

                email_items.append({
                    "name": product.get("name", "Product"),
                    "quantity": quantity,
                    "unit_price": price,
                    "amount": amount
                })

                validated_items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "amount": amount
                })

                
            # Create the order header.
            order_data = {
                "customer_id": customer["id"],
                "order_date": date.today(),
                "status": "Pending"
            }

            created_order = db.execute(
                insert(orders)
                .values(**order_data)
                .returning(orders)
            ).mappings().one()

            # Create every order item in the same transaction.
            saved_items = []

            for item in validated_items:
                saved_item = db.execute(
                    insert(order_items)
                    .values(
                        order_id=created_order["id"],
                        **item
                    )
                    .returning(order_items)
                ).mappings().one()

                saved_items.append(dict(saved_item))

            result = {
                "order": dict(created_order),
                "items": saved_items,
                "total": round(order_total, 2),
                "message": "Order placed successfully."
            }

        # The database transaction has committed successfully here.
        # An email failure must not undo the saved order.
        
        print("SMTP HOST:", os.getenv("SMTP_HOST"))
        print("SMTP PORT:", os.getenv("SMTP_PORT"))
        print("SMTP USERNAME SET:", bool(os.getenv("SMTP_USERNAME")))
        print("SMTP PASSWORD SET:", bool(os.getenv("SMTP_PASSWORD")))
        print("SMTP FROM:", os.getenv("SMTP_FROM"))





        try:
            send_order_confirmation_email(
                to_email=customer["email"],
                order=result["order"],
                items=email_items,
                total=result["total"]
            )

            result["email_sent"] = True

        except Exception as email_error:
            print(
                f"Order {result['order']['id']} saved, "
                f"but confirmation email failed: {email_error}"
            )

            result["email_sent"] = False

        return result

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


















@app.post("/api/{table}")
def create_record(
    table: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):

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
def get_record(
    table: str,
    record_id: int,
    current_user: dict = Depends(get_current_user)
):

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
def list_records(
    table: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Validate table
        # -------------------------------------------------

        if table not in metadata.tables:

            raise HTTPException(
                status_code=404,
                detail=f"Unknown table: {table}"
            )

        t = metadata.tables[table]

        # -------------------------------------------------
        # Select columns
        # -------------------------------------------------

        columns = [
            c
            for c in t.c
            if c.name != "password"
        ]

        query = select(*columns)

        # -------------------------------------------------
        # Generic query-parameter filtering
        #
        # Example:
        #
        # /api/order_items?order_id=5
        #
        # becomes:
        #
        # order_items.order_id == 5
        # -------------------------------------------------

        for field_name, field_value in request.query_params.items():

            if field_name not in t.c:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unknown filter field "
                        f"'{field_name}' for table '{table}'"
                    )
                )

            column = t.c[field_name]

            # Convert numeric values when appropriate
            try:

                python_type = column.type.python_type

                if python_type is int:
                    converted_value = int(field_value)

                elif python_type is float:
                    converted_value = float(field_value)

                elif python_type is bool:
                    converted_value = (
                        field_value.lower()
                        in ("true", "1", "yes")
                    )

                else:
                    converted_value = field_value

            except (AttributeError, ValueError):

                converted_value = field_value

            query = query.where(
                column == converted_value
            )

        # -------------------------------------------------
        # Execute
        # -------------------------------------------------

        result = db.execute(query)

        rows = [
            dict(row)
            for row in result.mappings()
        ]

        # -------------------------------------------------
        # Add reference display values
        # -------------------------------------------------

        entity_config = (
            app_config
            .get("entities", {})
            .get(table, {})
        )

        fields_config = entity_config.get(
            "fields",
            []
        )

        for field_config in fields_config:

            if field_config.get("type") != "reference":
                continue

            field_name = field_config.get("name")

            reference = field_config.get(
                "reference",
                {}
            )

            target_entity = reference.get(
                "entity"
            )

            value_field = reference.get(
                "valueField",
                "id"
            )

            label_field = reference.get(
                "labelField",
                value_field
            )

            if not target_entity:
                continue

            target_table = metadata.tables.get(
                target_entity
            )

            if target_table is None:
                continue

            if field_name not in t.c:
                continue

            target_column = target_table.c.get(
                value_field
            )

            target_label_column = target_table.c.get(
                label_field
            )

            if (
                target_column is None
                or target_label_column is None
            ):
                continue

            reference_values = {
                row[field_name]
                for row in rows
                if row.get(field_name) is not None
            }

            if not reference_values:
                continue

            reference_query = select(
                target_column,
                target_label_column
            ).where(
                target_column.in_(
                    reference_values
                )
            )

            reference_result = db.execute(
                reference_query
            )

            display_map = {
                row[0]: row[1]
                for row in reference_result
            }

            for row in rows:

                value = row.get(field_name)

                row[
                    f"{field_name}__display"
                ] = display_map.get(value)

        return rows

    finally:

        db.close()

@app.delete("/api/{table}/{id}")
def delete_record(
    table: str,
    id: int,
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    t = get_table(table)

    db.execute(
        delete(t).where(t.c.id == id)
    )

    db.commit()
    db.close()

    return {"status": "deleted"}


@app.put("/api/{table}/{id}")
def update_record(
    table: str,
    id: int,
    data: dict,
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        t = get_table(table)

        # Never update the primary key
        data.pop("id", None)

        result = db.execute(
            update(t)
            .where(t.c.id == id)
            .values(**data)
            .returning(t)
        )

        updated = result.mappings().first()

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail=f"{table} record {id} not found"
            )

        db.commit()

        return dict(updated)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/api/admin/add-inventory-images")
def add_inventory_images():

    db = SessionLocal()

    try:
        db.execute(text("""
            ALTER TABLE inventory
            ADD COLUMN IF NOT EXISTS images JSON
            NOT NULL DEFAULT '[]'::json
        """))

        db.commit()

        # Reload metadata so the dynamic model includes
        # the newly added database column.
        load_schema()

        return {
            "status": "ok",
            "message": "Inventory images column is ready."
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()


@app.post("/api/inventory/{inventory_id}/images")
def upload_inventory_images(
    inventory_id: int,
    files: list[UploadFile] = File(...)
):
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image
    MAX_IMAGES = 10

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one image."
        )

    if len(files) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"You can upload at most {MAX_IMAGES} images at a time."
        )

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise HTTPException(
            status_code=500,
            detail="Cloudinary environment variables are not configured."
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )

    uploaded_urls = []
    db = SessionLocal()

    try:
        t = get_table("inventory")

        # Confirm the inventory item exists.
        existing = db.execute(
            select(t.c.id).where(t.c.id == inventory_id)
        ).first()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Inventory item {inventory_id} not found."
            )
        print("INVENTORY TABLE COLUMNS:", list(t.c.keys()))    
        if "images" not in t.c:
            raise HTTPException(
                status_code=500,
                detail="Inventory images column is missing."
            )

        # Validate and upload each image.
        for file in files:
            if file.content_type not in (
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif"
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image type: {file.filename}"
                )

            content = file.file.read(MAX_FILE_SIZE + 1)

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} exceeds the 5 MB limit."
                )

            if not content:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is empty."
                )

            # Reset the stream before passing it to Cloudinary.
            file.file.seek(0)

            result = cloudinary.uploader.upload(
                file.file,
                folder=f"inventory/{inventory_id}",
                resource_type="image"
            )

            uploaded_urls.append(result["secure_url"])

        # Preserve existing images and append the new URLs.
        row = db.execute(
            select(t.c.images).where(t.c.id == inventory_id)
        ).first()

        existing_urls = list(row[0] or [])

        updated_urls = existing_urls + uploaded_urls

        db.execute(
            update(t)
            .where(t.c.id == inventory_id)
            .values(images=updated_urls)
        )

        db.commit()

        return {
            "status": "ok",
            "inventory_id": inventory_id,
            "images": updated_urls,
            "uploaded_count": len(uploaded_urls)
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )

    finally:
        db.close()

        for file in files:
            file.file.close()





@app.delete("/api/inventory/{inventory_id}/images")
def remove_inventory_image(inventory_id: int, url: str):
    db = SessionLocal()

    try:
        t = get_table("inventory")

        row = db.execute(
            select(t.c.images)
            .where(t.c.id == inventory_id)
        ).first()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Inventory item not found."
            )

        images = list(row[0] or [])

        if url not in images:
            raise HTTPException(
                status_code=404,
                detail="Image not found on this inventory item."
            )

        # Remove the image URL from the database array.
        updated_images = [image for image in images if image != url]

        db.execute(
            update(t)
            .where(t.c.id == inventory_id)
            .values(images=updated_images)
        )
        db.commit()

        # Best-effort deletion from Cloudinary.
        # A Cloudinary deletion failure won't undo the database change.
        try:
            parsed = urlparse(url)
            parts = parsed.path.split("/")

            upload_index = parts.index("upload")
            public_id_parts = parts[upload_index + 1:]

            # Remove the version component, such as v1792648938.
            if public_id_parts and public_id_parts[0].startswith("v"):
                public_id_parts = public_id_parts[1:]

            public_id = "/".join(public_id_parts)

            # Remove the file extension.
            public_id = public_id.rsplit(".", 1)[0]

            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                secure=True
            )

            cloudinary.uploader.destroy(
                public_id,
                resource_type="image"
            )
        except Exception as cloudinary_error:
            print("Cloudinary image deletion failed:", cloudinary_error)

        return {
            "status": "ok",
            "inventory_id": inventory_id,
            "images": updated_images
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()





@app.post("/api/inventory/images/upload")
def upload_inventory_images_before_save(
    files: list[UploadFile] = File(...)
):
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image
    MAX_IMAGES = 10

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one image."
        )

    if len(files) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"You can upload at most {MAX_IMAGES} images at a time."
        )

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise HTTPException(
            status_code=500,
            detail="Cloudinary environment variables are not configured."
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )

    uploaded_urls = []

    try:
        for file in files:
            if file.content_type not in (
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif"
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image type: {file.filename}"
                )

            content = file.file.read(MAX_FILE_SIZE + 1)

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} exceeds the 5 MB limit."
                )

            if not content:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is empty."
                )

            file.file.seek(0)

            result = cloudinary.uploader.upload(
                file.file,
                folder="inventory/pending",
                resource_type="image"
            )

            uploaded_urls.append(result["secure_url"])

        return {
            "status": "ok",
            "images": uploaded_urls,
            "uploaded_count": len(uploaded_urls)
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )

    finally:
        for file in files:
            file.file.close()




def send_order_confirmation_email(
    to_email,
    order,
    items,
    total
):
    required_settings = [
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM"
    ]

    missing = [
        key for key in required_settings
        if not os.getenv(key)
    ]

    if missing:
        raise RuntimeError(
            "Missing email settings: " + ", ".join(missing)
        )

    message = EmailMessage()
    message["Subject"] = (
        f"Order Confirmation #{order['id']}"
    )
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = to_email

    lines = [
        "Thank you for your order!",
        "",
        f"Order number: {order['id']}",
        f"Order date: {order['order_date']}",
        f"Status: {order['status']}",
        "",
        "Items:"
    ]

    for item in items:
        lines.append(
            f"- {item['name']} x {item['quantity']} "
            f"@ {item['unit_price']:.2f} "
            f"= {item['amount']:.2f}"
        )

    lines.extend([
        "",
        f"Order total: {total:.2f}",
        "",
        "Payment has not been collected. "
        "This order was placed in test mode.",
        "",
        "We will notify you when your order status changes."
    ])

    message.set_content("\n".join(lines))

    with smtplib.SMTP(
        os.environ["SMTP_HOST"],
        int(os.getenv("SMTP_PORT", "587")),
        timeout=20
    ) as server:
        server.starttls()
        server.login(
            os.environ["SMTP_USERNAME"],
            os.environ["SMTP_PASSWORD"]
        )
        server.send_message(message)




@app.get("/")
def root():
    return {"status": "OK"}






  
