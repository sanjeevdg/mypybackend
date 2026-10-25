from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    Numeric,
    JSON,
    ForeignKey,
    func
)

from database import metadata


TYPE_MAP = {
    "text": String,
    "email": String,
    "number": Integer,
    "password": String,
    "checkbox": Boolean,
    "boolean": Boolean,
    "datetime": DateTime,
    "date": Date,
    "select": String,
    "file": String,
    "autocomplete": String,
    "reference": Integer,
    "currency": Numeric(12, 2),
    "json": JSON
}


def build_models(config):

    for entity_name, entity in config["entities"].items():

        db_table_name = entity.get(
            "table",
            entity_name
        )

        # Make sure table name is actually a string
        if not isinstance(db_table_name, str):
            raise Exception(
                f"Invalid table name for entity "
                f"'{entity_name}': {db_table_name}"
            )

        columns = [
            Column(
                "id",
                Integer,
                primary_key=True
            )
        ]

        for field in entity["fields"]:

            field_name = field["name"]

            if field_name == "id":
                continue

            field_type = field["type"]

            # -----------------------------

            # Link each customer to an authentication user
            if entity_name == "customers" and field_name == "user_id":
                columns.append(
                    Column(
                        "user_id",
                        Integer,
                        nullable=True,
                        unique=True
                    )
                )
                continue

            # Reference field
            # -----------------------------
            if field_type == "reference":

                reference = field.get("reference")

                if not reference:
                    raise Exception(
                        f"Reference field '{field_name}' "
                        f"has no reference configuration"
                    )

                target_entity = reference["entity"]

                if target_entity not in config["entities"]:
                    raise Exception(
                        f"Reference field '{field_name}' "
                        f"points to unknown entity "
                        f"'{target_entity}'"
                    )

                target_table = config["entities"][target_entity].get(
                    "table",
                    target_entity
                )

                target_column = reference.get(
                    "valueField",
                    "id"
                )

                on_delete = reference.get("onDelete")

                foreign_key = ForeignKey(
                    f"{target_table}.{target_column}",
                    ondelete=(
                        on_delete.upper()
                        if on_delete
                        else None
                    )
                )

                columns.append(
                    Column(
                        field_name,
                        Integer,
                        foreign_key
                    )
                )

            # -----------------------------
            # Normal field
            # -----------------------------
            # -----------------------------
            # Normal field
            # -----------------------------
            else:

                if entity_name == "customers" and field_name == "user_id":
                    columns.append(
                        Column(
                            "user_id",
                            Integer,
                            nullable=True,
                            unique=True
                        )
                    )
                    continue
                sql_type = TYPE_MAP.get(field_type)

                if sql_type is None:
                    raise Exception(
                        f"Unknown field type: {field_type}"
                    )

                if field_name == "createdAt":

                    columns.append(
                        Column(
                            field_name,
                            sql_type,
                            server_default=func.now()
                        )
                    )

                elif field_name == "updatedAt":

                    columns.append(
                        Column(
                            field_name,
                            sql_type,
                            server_default=func.now(),
                            onupdate=func.now()
                        )
                    )

                else:

                    columns.append(
                        Column(
                            field_name,
                            sql_type
                        )
                    )
        print(
            f"Fields for {entity_name}:",
            [field["name"] for field in entity["fields"]]
        )            
        print(
            f"Creating table: {db_table_name}"
        )

        Table(
            db_table_name,
            metadata,
            *columns
        )

    return metadata