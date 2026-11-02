from sqlalchemy import text
from database import engine

with engine.begin() as conn:

    print("Creating foreign key...")



    conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS discount_batch_items (
                                id SERIAL PRIMARY KEY,

                                discount_batch_id INTEGER NOT NULL
                                    REFERENCES discount_batches(id)
                                    ON DELETE CASCADE,

                                order_item_id INTEGER NOT NULL
                                    REFERENCES order_items(id)
                                    ON DELETE RESTRICT,

                                order_id INTEGER NOT NULL
                                    REFERENCES orders(id)
                                    ON DELETE RESTRICT,

                                product_id INTEGER NOT NULL
                                    REFERENCES inventory(id)
                                    ON DELETE RESTRICT,

                                quantity NUMERIC,

                                original_amount NUMERIC(12, 2),

                                discount_type VARCHAR(50),

                                discount_value NUMERIC(12, 2),

                                discount_amount NUMERIC(12, 2),

                                final_amount NUMERIC(12, 2),

                                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
    """))

    print("Foreign key created successfully.")


