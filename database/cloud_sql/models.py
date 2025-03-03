import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


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
