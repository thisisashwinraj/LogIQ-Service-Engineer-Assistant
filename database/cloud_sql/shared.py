import json
import random
import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


class Appliances:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            "config/cloud_sql_editor_service_account_key.json"
        )

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]

    def _get_connection(self):
        conn = self.connector.connect(
            "logiq-project:us-central1:logiq-mysql-db",
            "pymysql",
            user="root",
            password=self.db_password,
            db="logiq_db",
        )
        return conn

    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS appliances (
                    appliance_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    model_number VARCHAR(255) NOT NULL UNIQUE,
                    appliance_name VARCHAR(255) NOT NULL,
                    brand VARCHAR(255) NOT NULL,
                    category VARCHAR(255) NOT NULL,
                    sub_category VARCHAR(255) NOT NULL,
                    appliance_image_url VARCHAR(255) NOT NULL,
                    warranty_period INTEGER NOT NULL,
                    launch_date DATE NOT NULL,
                    energy_rating INTEGER CHECK(energy_rating BETWEEN 1 AND 5) NOT NULL,
                    availability_status VARCHAR(255) CHECK(availability_status IN ('available', 'out_of_stock', 'discontinued')) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
                );
            """
            )
            db_conn.execute(query)

    def add_appliance(
        self,
        model_number,
        appliance_name,
        brand,
        category,
        sub_category,
        appliance_image_url,
        warranty_period,
        launch_date,
        energy_rating,
        availability_status,
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                INSERT INTO appliances (
                model_number, appliance_name, brand, category, sub_category, appliance_image_url,
                warranty_period, launch_date, energy_rating, availability_status
                )
                VALUES (
                :model_number, :appliance_name, :brand, :category, :sub_category, :appliance_image_url,
                :warranty_period, :launch_date, :energy_rating, :availability_status
                )
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "model_number": model_number,
                    "appliance_name": appliance_name,
                    "brand": brand,
                    "category": category,
                    "sub_category": sub_category,
                    "appliance_image_url": appliance_image_url,
                    "warranty_period": warranty_period,
                    "launch_date": launch_date,
                    "energy_rating": energy_rating,
                    "availability_status": availability_status,
                },
            )

            db_conn.commit()

    def update_appliance(self, model_number, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE appliances SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE model_number = :model_number;"
            update_values["model_number"] = model_number

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_appliance(self, model_number):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM appliances
                WHERE model_number = :model_number
                """
            )
            db_conn.execute(query, parameters={"model_number": model_number})

            db_conn.commit()

    def fetch_all_appliances(self, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if columns:
                query = sqlalchemy.text(
                    f"SELECT {', '.join(columns)} FROM appliances")
            else:
                query = sqlalchemy.text("SELECT * FROM appliances")

            result = db_conn.execute(query).fetchall()
            return result

    def fetch_all_sub_categories(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                "SELECT DISTINCT sub_category FROM appliances")
            result = db_conn.execute(query).fetchall()

            sub_categories = [category[0] for category in result]
            return sub_categories

    def fetch_brands_by_sub_category(self, sub_category):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT brand FROM appliances
                WHERE sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query, parameters={"sub_category": sub_category}
            ).fetchall()

            brands = [brand[0] for brand in result]
            return brands

    def fetch_models_by_brand_and_sub_category(self, brand, sub_category):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT model_number FROM appliances
                WHERE brand = :brand AND sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query, parameters={
                    "brand": brand, "sub_category": sub_category}
            ).fetchall()

            model_numbers = [model_number[0] for model_number in result]
            return model_numbers


class ServiceGuides:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            "config/cloud_sql_editor_service_account_key.json"
        )

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]

    def _get_connection(self):
        conn = self.connector.connect(
            "logiq-project:us-central1:logiq-mysql-db",
            "pymysql",
            user="root",
            password=self.db_password,
            db="logiq_db",
        )
        return conn

    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS service_guides (
                    guide_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    model_number VARCHAR(255) NOT NULL UNIQUE,
                    guide_name VARCHAR(255) NOT NULL,
                    guide_file_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY (model_number) REFERENCES appliances(model_number)
                );
                """
            )
            db_conn.execute(query)

    def add_service_guide(self, model_number, guide_name, guide_file_url):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                INSERT INTO service_guides (model_number, guide_name, guide_file_url)
                VALUES (:model_number, :guide_name, :guide_file_url)
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "model_number": model_number,
                    "guide_name": guide_name,
                    "guide_file_url": guide_file_url,
                },
            )

            db_conn.commit()

    def update_service_guide(self, guide_id, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE service_guides SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE guide_id = :guide_id;"
            update_values["guide_id"] = guide_id

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_service_guide(self, guide_id):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM service_guides
                WHERE guide_id = :guide_id
                """
            )

            db_conn.execute(query, parameters={"guide_id": guide_id})

            db_conn.commit()

    def fetch_guide_by_model_number(self, model_number):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT guide_name, guide_file_url
                FROM service_guides
                WHERE model_number = :model_number
                """
            )

            result = db_conn.execute(
                query, parameters={"model_number": model_number}
            ).fetchone()

            return result

    def fetch_model_number_of_all_guides(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text("SELECT model_number FROM service_guides")
            result = db_conn.execute(query)

            return result.fetchall()

    def add_troubleshoot_guide_for_category(
            self, sub_category, guide_file_url):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT model_number
                FROM appliances
                WHERE sub_category = :sub_category
                """
            )

            model_numbers = db_conn.execute(
                query, parameters={"sub_category": sub_category}
            ).fetchall()

            for model_number in model_numbers:
                model_number = model_number[0]
                guide_name = f"Service Guide for {model_number}"

                query = sqlalchemy.text(
                    """
                    INSERT INTO service_guides (model_number, guide_name, guide_file_url)
                    VALUES (:model_number, :guide_name, :guide_file_url)
                    """
                )

                db_conn.execute(
                    query,
                    parameters={
                        "model_number": model_number,
                        "guide_name": guide_name,
                        "guide_file_url": guide_file_url,
                    },
                )

            db_conn.commit()


class Customers:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            "config/cloud_sql_editor_service_account_key.json"
        )

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]

    def _get_connection(self):
        conn = self.connector.connect(
            "logiq-project:us-central1:logiq-mysql-db",
            "pymysql",
            user="root",
            password=self.db_password,
            db="logiq_db",
        )
        return conn

    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    username VARCHAR(255) PRIMARY KEY,
                    first_name VARCHAR(255) NOT NULL,
                    last_name VARCHAR(255) NOT NULL,
                    dob DATE NOT NULL,
                    gender VARCHAR(20) CHECK(gender IN ('Male', 'Female', 'Non-binary', 'Other')),
                    email VARCHAR(255) NOT NULL UNIQUE,
                    phone_number VARCHAR(20) NOT NULL UNIQUE,
                    profile_picture TEXT NOT NULL,
                    street TEXT NOT NULL,
                    district VARCHAR(255) NOT NULL,
                    city VARCHAR(255) NOT NULL,
                    state VARCHAR(255) NOT NULL,
                    country VARCHAR(255) NOT NULL,
                    zip_code VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            )
            db_conn.execute(query)

    def add_customer(
        self,
        username,
        first_name,
        last_name,
        dob,
        gender,
        email,
        phone_number,
        profile_picture,
        street,
        city,
        district,
        state,
        country,
        zip_code,
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                INSERT INTO customers (username, first_name, last_name, dob, gender, email, phone_number, profile_picture, street, district, city, state, country, zip_code)
                VALUES (:username, :first_name, :last_name, :dob, :gender, :email, :phone_number, :profile_picture, :street, :district, :city, :state, :country, :zip_code)
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone_number": phone_number,
                    "profile_picture": profile_picture,
                    "dob": dob,
                    "street": street,
                    "district": district,
                    "city": city,
                    "state": state,
                    "country": country,
                    "zip_code": zip_code,
                    "gender": gender,
                },
            )

            db_conn.commit()

    def update_customer(self, username, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE customers SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE username = :username;"
            update_values["username"] = username

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_customer(self, username):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM customers
                WHERE username = :username
                """
            )

            db_conn.execute(query, parameters={"username": username})

            db_conn.commit()

    def fetch_customer_by_username(self, username, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if columns:
                query = sqlalchemy.text(
                    f"SELECT {
                        ', '.join(columns)} FROM customers WHERE username = :username"
                )
            else:
                query = sqlalchemy.text(
                    "SELECT * FROM customers WHERE username = :username"
                )

            result = db_conn.execute(
                query, parameters={"username": username}
            ).fetchone()

            return result

    def fetch_all_customers(self, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        if columns:
            query = sqlalchemy.text(
                f"SELECT {', '.join(columns)} FROM customers")
        else:
            query = sqlalchemy.text("SELECT * FROM customers")

        with pool.connect() as db_conn:
            result = db_conn.execute(query)

        return result.fetchall()


class Engineers:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            "config/cloud_sql_editor_service_account_key.json"
        )

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]

    def _get_connection(self):
        conn = self.connector.connect(
            "logiq-project:us-central1:logiq-mysql-db",
            "pymysql",
            user="root",
            password=self.db_password,
            db="logiq_db",
        )
        return conn

    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS engineers (
                    engineer_id VARCHAR(255) PRIMARY KEY,
                    first_name VARCHAR(255) NOT NULL,
                    last_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    phone_number VARCHAR(20) NOT NULL UNIQUE,
                    availability BOOLEAN DEFAULT TRUE NOT NULL,
                    active_tickets INTEGER DEFAULT 0 NOT NULL,
                    street TEXT NOT NULL,
                    city VARCHAR(255) NOT NULL,
                    district VARCHAR(255) NOT NULL,
                    state VARCHAR(255) NOT NULL,
                    country VARCHAR(255) NOT NULL,
                    zip_code VARCHAR(20) NOT NULL,
                    specializations JSON NOT NULL,
                    skills JSON NOT NULL,
                    rating FLOAT DEFAULT 5 NOT NULL,
                    training_id INTEGER,
                    reward_points INTEGER DEFAULT 0 NOT NULL,
                    profile_picture TEXT,
                    language_proficiency JSON NOT NULL,
                    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            db_conn.execute(query)

    def add_engineer(
        self,
        first_name,
        last_name,
        email,
        phone_number,
        availability,
        street,
        city,
        district,
        state,
        country,
        zip_code,
        specializations,
        skills,
        training_id,
        profile_picture,
        language_proficiency,
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            engineer_id = f"ENGR{
                random.randint(
                    1, 9)}{
                first_name[0].upper()}{
                random.randint(
                    1, 9)}{
                        last_name[0].upper()}{
                            random.randint(
                                100, 999)}"

            query = sqlalchemy.text(
                """
                INSERT INTO engineers (engineer_id, first_name, last_name, email, phone_number, availability, street, city, district, state, country, zip_code, specializations, skills, training_id, profile_picture, language_proficiency)
                VALUES (:engineer_id, :first_name, :last_name, :email, :phone_number, :availability, :street, :city, :district, :state, :country, :zip_code, :specializations, :skills, :training_id, :profile_picture, :language_proficiency)
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "engineer_id": engineer_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone_number": phone_number,
                    "availability": availability,
                    "street": street,
                    "city": city,
                    "district": district,
                    "state": state,
                    "country": country,
                    "zip_code": zip_code,
                    "specializations": json.dumps(specializations),
                    "skills": json.dumps(skills),
                    "training_id": training_id,
                    "profile_picture": profile_picture,
                    "language_proficiency": json.dumps(language_proficiency),
                },
            )

            db_conn.commit()
            return engineer_id

    def update_engineer(self, engineer_id, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE engineers SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE engineer_id = :engineer_id;"
            update_values["engineer_id"] = engineer_id

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_engineer(self, engineer_id):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM engineers
                WHERE engineer_id = :engineer_id
                """
            )

            db_conn.execute(query, parameters={"engineer_id": engineer_id})
            db_conn.commit()

    def fetch_engineer_by_id(self, engineer_id, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if columns:
                query = sqlalchemy.text(
                    f"SELECT {
                        ', '.join(columns)} FROM engineers WHERE engineer_id = :engineer_id"
                )
            else:
                query = sqlalchemy.text(
                    "SELECT * FROM engineers WHERE engineer_id = :engineer_id"
                )

            result = db_conn.execute(
                query, parameters={"engineer_id": engineer_id}
            ).fetchone()

            results_map = {}

            for idx, column in enumerate(columns):
                results_map[column] = result[idx]

            return results_map

    def fetch_available_engineer_for_service_request(
        self, district, specialization, skill
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT engineer_id
                FROM engineers
                WHERE availability = True AND district = :district AND JSON_CONTAINS(skills, JSON_QUOTE(:skill)) AND JSON_CONTAINS(specializations, JSON_QUOTE(:specialization))
                ORDER BY active_tickets ASC
                LIMIT 10
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "district": district,
                    "skill": skill,
                    "specialization": specialization,
                },
            ).fetchall()

            if result:
                return list(result[0])
            else:
                return []

    def fetch_all_engineers(self, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if columns:
                query = sqlalchemy.text(
                    f"SELECT {', '.join(columns)} FROM engineers")
            else:
                query = sqlalchemy.text("SELECT * FROM engineers")

            result = db_conn.execute(query)
            return result.fetchall()


class CustomerAppliances:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            "config/cloud_sql_editor_service_account_key.json"
        )

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]

    def _get_connection(self):
        conn = self.connector.connect(
            "logiq-project:us-central1:logiq-mysql-db",
            "pymysql",
            user="root",
            password=self.db_password,
            db="logiq_db",
        )
        return conn

    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS customer_appliances (
                    customer_appliance_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    customer_id VARCHAR(255) NOT NULL,
                    category VARCHAR(255) NOT NULL,
                    sub_category VARCHAR(255) NOT NULL,
                    brand VARCHAR(255) NOT NULL,
                    model_number VARCHAR(255) NOT NULL,
                    serial_number VARCHAR(255) NOT NULL UNIQUE,
                    purchase_date DATE NOT NULL,
                    warranty_period INTEGER NOT NULL,
                    warranty_expiration DATE NOT NULL,
                    purchased_from VARCHAR(255) NOT NULL,
                    seller VARCHAR(255) NOT NULL,
                    installation_date DATE NOT NULL,
                    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status VARCHAR(255) CHECK(status IN ('active', 'inactive')) NOT NULL DEFAULT 'active'
                );
                """
            )
            db_conn.execute(query)

    def add_customer_appliance(
        self,
        customer_id,
        category,
        sub_category,
        brand,
        model_number,
        serial_number,
        purchase_date,
        warranty_period,
        warranty_expiration,
        purchased_from,
        seller,
        installation_date,
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                INSERT INTO customer_appliances (customer_id, category, sub_category, brand, model_number, serial_number, purchase_date, warranty_period, warranty_expiration, purchased_from, seller, installation_date)
                VALUES (:customer_id, :category, :sub_category, :brand, :model_number, :serial_number, :purchase_date, :warranty_period, :warranty_expiration, :purchased_from, :seller, :installation_date)
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "customer_id": customer_id,
                    "category": category,
                    "sub_category": sub_category,
                    "brand": brand,
                    "model_number": model_number,
                    "serial_number": serial_number,
                    "purchase_date": purchase_date,
                    "warranty_period": warranty_period,
                    "warranty_expiration": warranty_expiration,
                    "purchased_from": purchased_from,
                    "seller": seller,
                    "installation_date": installation_date,
                },
            )
            db_conn.commit()

    def update_customer_appliance_by_serial_number(
            self, serial_number, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE customer_appliances SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE serial_number = :serial_number;"
            update_values["serial_number"] = serial_number

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def fetch_customer_appliance_by_serial_number(
            self, serial_number, columns=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if columns:
                query = sqlalchemy.text(
                    f"SELECT {
                        ', '.join(columns)} FROM customer_appliances WHERE serial_number = :serial_number"
                )
            else:
                query = sqlalchemy.text(
                    "SELECT * FROM customer_appliances WHERE serial_number = :serial_number"
                )

            result = db_conn.execute(
                query, parameters={"serial_number": serial_number}
            ).fetchone()

            return list(result)

    def delete_customer_appliance(self, serial_number):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM customer_appliances
                WHERE serial_number = :serial_number
                """
            )

            db_conn.execute(query, parameters={"serial_number": serial_number})
            db_conn.commit()
