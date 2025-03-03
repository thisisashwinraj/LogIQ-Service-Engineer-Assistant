import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


class MigrateCustomers:
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

    def update_customer(self, username, **kwargs):
        try:
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

                return True

        except Exception as error:
            return False


class MigrateEngineers:
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

    def update_engineer(self, engineer_id, **kwargs):
        try:
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

                return True

        except Exception as error:
            return False

    def toggle_engineer_availability(self, engineer_id):
        try:
            pool = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=self._get_connection,
            )

            with pool.connect() as db_conn:
                update_query = """
                    UPDATE engineers
                    SET availability = NOT availability
                    WHERE engineer_id = :engineer_id;
                """
                update_values = {"engineer_id": engineer_id}
                query = sqlalchemy.text(update_query)

                db_conn.execute(query, parameters=update_values)
                db_conn.commit()

                return True

        except Exception as error:
            return False
