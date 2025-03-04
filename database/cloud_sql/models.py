import json
import random
import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


class ModelCustomerAppliances:
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


class ModelCustomerAppliances:
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
                    appliance_image_url VARCHAR(255) NOT NULL,
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
        appliance_image_url,
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        try:
            with pool.connect() as db_conn:
                query = sqlalchemy.text(
                    """
                    INSERT INTO customer_appliances (customer_id, category, sub_category, brand, model_number, serial_number, purchase_date, warranty_period, warranty_expiration, purchased_from, seller, installation_date, appliance_image_url)
                    VALUES (:customer_id, :category, :sub_category, :brand, :model_number, :serial_number, :purchase_date, :warranty_period, :warranty_expiration, :purchased_from, :seller, :installation_date, :appliance_image_url)
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
                        "appliance_image_url": appliance_image_url,
                    },
                )

                db_conn.commit()
                return True

        except Exception as error:
            return False


class ModelServiceGuides:
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

    def add_service_guide_by_category(
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


class ModelCustomers:
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


class ModelEngineers:
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
