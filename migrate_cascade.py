from sqlalchemy import text
from database import engine

with engine.begin() as conn:

    print("Creating foreign key...")

    conn.execute(text("""
        ALTER TABLE orders
        ADD CONSTRAINT orders_customer_id_fkey
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE CASCADE
    """))

    print("Foreign key created successfully.")