import random
import sqlite3
from datetime import datetime


class Appliances:
    def __init__(self, db_name="database/persistent/general.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appliances (
                appliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT NOT NULL UNIQUE,
                appliance_name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category TEXT NOT NULL,
                sub_category TEXT NOT NULL,
                warranty_period INTEGER,
                launch_date DATE,
                energy_rating INTEGER CHECK(energy_rating BETWEEN 1 AND 5),
                availability_status TEXT CHECK(availability_status IN ('available', 'out_of_stock', 'discontinued')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        self.conn.commit()

    def add_appliance(
        self,
        model_number,
        appliance_name,
        brand,
        category,
        sub_category,
        warranty_period,
        launch_date,
        energy_rating,
        availability_status,
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO appliances (model_number, appliance_name, brand, category, sub_category, warranty_period, launch_date, energy_rating, availability_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                model_number,
                appliance_name,
                brand,
                category,
                sub_category,
                warranty_period,
                launch_date,
                energy_rating,
                availability_status,
            ),
        )
        self.conn.commit()

    def update_appliance(self, model_number, **kwargs):
        cursor = self.conn.cursor()

        update_query = "UPDATE appliances SET "
        update_values = []

        for key, value in kwargs.items():
            update_query += f"{key} = ?, "
            update_values.append(value)

        update_query = update_query[:-2]
        update_query += " WHERE model_number = ?"
        update_values.append(model_number)

        cursor.execute(update_query, tuple(update_values))
        self.conn.commit()

    def delete_appliance(self, model_number):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM appliances WHERE model_number = ?", (model_number,))
        self.conn.commit()

    def fetch_all_categories(self):
        cursor = self.conn.cursor()

        cursor.execute("SELECT DISTINCT sub_category FROM appliances")
        sub_categories = [category[0] for category in cursor.fetchall()]

        return sub_categories

    def fetch_brands_by_sub_category(self, sub_category):
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT DISTINCT brand FROM appliances WHERE sub_category = ?",
            (sub_category,),
        )
        brands = [brand[0] for brand in cursor.fetchall()]

        return brands

    def fetch_models_by_brand_and_sub_category(self, brand, sub_category):
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT DISTINCT model_number FROM appliances WHERE brand = ? and sub_category = ?",
            (
                brand,
                sub_category,
            ),
        )
        model_numbers = [model_number[0] for model_number in cursor.fetchall()]

        return model_numbers

    def fetch_all_appliances(self):
        cursor = self.conn.cursor()
        cursor.execute("""SELECT model_number FROM appliances""")
        return cursor.fetchall()

    def close_connection(self):
        self.conn.close()


class ServiceGuides:
    def __init__(self, db_name="database/persistent/general.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS service_guides (
                guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT NOT NULL UNIQUE,
                guide_name TEXT NOT NULL,
                guide_file_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_number) REFERENCES appliances(model_number)
            );
        """
        )
        self.conn.commit()

    def add_service_guide(self, model_number, guide_name, guide_file_url):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO service_guides (model_number, guide_name, guide_file_url)
            VALUES (?, ?, ?)
        """,
            (model_number, guide_name, guide_file_url),
        )

        self.conn.commit()

    def update_service_guide(self, guide_id, **kwargs):
        cursor = self.conn.cursor()

        update_query = "UPDATE service_guides SET "
        update_values = []

        for key, value in kwargs.items():
            update_query += f"{key} = ?, "
            update_values.append(value)

        update_query = update_query[:-2]
        update_query += " WHERE guide_id = ?"
        update_values.append(guide_id)

        cursor.execute(update_query, tuple(update_values))
        self.conn.commit()

    def delete_service_guide(self, guide_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM service_guides WHERE guide_id = ?", (guide_id,))
        self.conn.commit()

    def fetch_guides_by_model_number(self, model_number):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT guide_name, guide_file_url FROM service_guides WHERE model_number = ?""",
            (model_number,),
        )
        return cursor.fetchone()

    def fetch_all_guides(self):
        cursor = self.conn.cursor()
        cursor.execute("""SELECT model_number FROM service_guides""")
        return cursor.fetchall()

    def add_troubleshoot_guide_for_category(self, sub_category, guide_file_url):
        cursor = self.conn.cursor()
        # cursor.execute("DROP TABLE service_guides")

        cursor.execute(
            """
            SELECT model_number FROM appliances WHERE sub_category = ?
        """,
            (sub_category,),
        )
        model_numbers = cursor.fetchall()

        for model in model_numbers:
            model_number = model[0]
            guide_name = f"Service Guide for {model_number}"

            cursor.execute(
                """
                INSERT INTO service_guides (model_number, guide_name, guide_file_url)
                VALUES (?, ?, ?)
            """,
                (model_number, guide_name, guide_file_url),
            )

        self.conn.commit()

    def close_connection(self):
        self.conn.close()


if __name__ == "__main__":
    appliance_db = Appliances()
    guide_db = ServiceGuides()

    """
    guide_db.add_troubleshoot_guide_for_category(
        sub_category='Freestanding Double Oven Gas Range',
        guide_file_url='data/service_guides/freestanding_double_oven_gas_range_service_guide.pdf',
    )
    """

    print(guide_db.fetch_guides_by_model_number("ALD10DT"))

    """
    print(appliance_db.fetch_appliances_by_sub_category("Amana"))

    brand = "Maytag"
    sub_category = "Freestanding Double Oven Gas Range"

    my_models = [
        "MGR6775ADB/Q/S/W", "MGR6875ADB/Q/S/W",   # 48-inch
    ]

    for model in my_models:
        appliance_db.add_appliance(
            model_number=model,
            appliance_name=f"{brand} {sub_category}",
            brand=brand,
            category="Gas Range",
            sub_category=sub_category,
            warranty_period=random.choice([18, 24, 30, 36]),
            launch_date=random.choice(["2024-04-27", "2022-11-23", "2024-08-19", "2023-03-22", "2024-02-06"]),
            energy_rating=random.choice([2.5, 3, 3.5, 4, 4.5]),
            availability_status=random.choice(["available", "out_of_stock"])
        )

        print(f"Done {model}")
    
    for i in appliance_db.fetch_appliances_by_sub_category(sub_category=sub_category):
        print(i)

    guide_db.add_service_guide(
        appliance_id=appliance_id,
        guide_name="X100 Fridge Troubleshooting Guide",
        guide_file_url="https://example.com/guides/x100_fridge_troubleshoot.pdf",
        guide_version="1.0"
    )

    guides = guide_db.fetch_guide_by_model_and_category("X100", "Refrigerator")
    print("Guides for X100 Refrigerator:", guides)

    appliance_db.close_connection()
    guide_db.close_connection()
    """
