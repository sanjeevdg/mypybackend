from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime
)
from database import metadata


TYPE_MAP = {
    "text": String,
    "email": String,
    "number": Integer,
    "checkbox": Boolean,
    "datetime":DateTime,
    "date":Date,
    "select":String,
    "file":String,
    "autocomplete":String
}

def build_models(config):

    for table_name, entity in config["entities"].items():

        columns = [
            Column("id", Integer, primary_key=True)
        ]

        for field in entity["fields"]:

            field_name = field["name"]
            field_type = field["type"]

            sql_type = TYPE_MAP.get(field_type)

            if sql_type is None:
                raise Exception(f"Unknown field type: {field_type}")

            columns.append(
                Column(field_name, sql_type)
            )

        Table(
            table_name,
            metadata,
            *columns
        )

    return metadata