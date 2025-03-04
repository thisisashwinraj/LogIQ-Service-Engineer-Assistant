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

    def fetch_distinct_appliance_data(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT sub_category, brand, model_number
                FROM appliances;
                """
            )

            cursor = db_conn.execute(query).fetchall()

        result = {}

        for sub_category, brand, model_number in cursor:
            if sub_category not in result:
                result[sub_category] = {}

            if brand not in result[sub_category]:
                result[sub_category][brand] = []

            result[sub_category][brand].append(model_number)

        return result

    def fetch_distinct_appliance_data_with_category(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT category, sub_category, brand, model_number
                FROM appliances;
                """
            )

            cursor = db_conn.execute(query).fetchall()

        result = {}

        for category, sub_category, brand, model_number in cursor:
            if category not in result:
                result[category] = {}

            if sub_category not in result[category]:
                result[category][sub_category] = {}

            if brand not in result[category][sub_category]:
                result[category][sub_category][brand] = []

            result[category][sub_category][brand].append(model_number)

        return result

    def fetch_distinct_appliance_categories(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT category
                FROM appliances
                """
            )

            result = db_conn.execute(query).fetchall()

            categories = [category[0] for category in result]
            return categories

    def fetch_distinct_appliance_sub_categories_by_category(
            self, category=None):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if category:
                query = sqlalchemy.text(
                    """
                    SELECT DISTINCT sub_category
                    FROM appliances
                    WHERE category = :category
                    """
                )

                result = db_conn.execute(
                    query, parameters={"category": category}
                ).fetchall()

            else:
                query = sqlalchemy.text(
                    """
                    SELECT DISTINCT sub_category
                    FROM appliances
                    """
                )

                result = db_conn.execute(query).fetchall()

            sub_categories = [sub_category[0] for sub_category in result]
            return sub_categories

    def fetch_category_by_sub_caegory(self, sub_category):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT category
                FROM appliances
                WHERE sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query, parameters={"sub_category": sub_category}
            ).fetchone()

            return str(result[0])

    def fetch_distinct_appliance_brands_by_sub_category(self, sub_category):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT brand
                FROM appliances
                WHERE sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query, parameters={"sub_category": sub_category}
            ).fetchall()

            brands = [brand[0] for brand in result]
            return brands

    def fetch_distinct_model_numbers_by_brand_and_sub_category(
        self, brand, sub_category
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT model_number
                FROM appliances
                WHERE brand = :brand
                AND sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query, parameters={
                    "brand": brand, "sub_category": sub_category}
            ).fetchall()

            model_numbers = [model_number[0] for model_number in result]
            return model_numbers

    def fetch_warranty_period_and_appliance_image_url_by_brand_sub_category_and_model_number(
        self, brand, sub_category, model_number
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT warranty_period, appliance_image_url
                FROM appliances
                WHERE brand = :brand
                AND sub_category = :sub_category
                AND model_number = :model_number
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "brand": brand,
                    "sub_category": sub_category,
                    "model_number": model_number,
                },
            ).fetchone()

            return int(result[0]), result[1]

    def fetch_best_appliances_by_energy_rating(self, count):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT category, model_number, brand, appliance_image_url
                FROM appliances
                WHERE appliance_id IN (5, 35, 80, 160)
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "count": count,
                },
            ).fetchall()

        return result

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


class QueryCustomerAppliances:
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

    def fetch_customer_appliance_data_by_customer_id(
            self, customer_id, limit=4):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if limit == -1:
                query = sqlalchemy.text(
                    """
                    SELECT category, sub_category, brand, model_number, purchased_from, seller, purchase_date, installation_date, warranty_period, warranty_expiration, appliance_image_url, serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY created_on DESC
                    """
                )

            else:
                query = sqlalchemy.text(
                    """
                    SELECT category, sub_category, brand, model_number, purchased_from, seller, purchase_date, installation_date, warranty_period, warranty_expiration, appliance_image_url, serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY created_on DESC
                    LIMIT :limit
                    """
                )

            result = db_conn.execute(
                query, parameters={"customer_id": customer_id, "limit": limit}
            ).fetchall()

        customer_appliances = {}

        for row in result:
            serial_number = row.serial_number

            appliance_details = {
                "category": row[0],
                "sub_category": row[1],
                "brand": row[2],
                "model_number": row[3],
                "serial_number": serial_number,
                "purchased_from": row[4],
                "seller": row[5],
                "purchase_date": row[6],
                "installation_date": row[7],
                "warranty_period": row[8],
                "warranty_expiration": row[9],
                "appliance_image_url": row[10],
                "serial_number": row[11],
            }

            customer_appliances[serial_number] = appliance_details

        return customer_appliances

    def fetch_appliance_serial_numbers_by_customer_id(
            self, customer_id, limit=4):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            if limit == -1:
                query = sqlalchemy.text(
                    """
                    SELECT serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY created_on DESC
                    """
                )

            else:
                query = sqlalchemy.text(
                    """
                    SELECT serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY installation_date DESC
                    LIMIT :limit
                    """
                )

            result = db_conn.execute(
                query, parameters={"customer_id": customer_id, "limit": limit}
            ).fetchall()

            serial_number = [serial_number[0] for serial_number in result]
            return serial_number

    def fetch_customer_appliance_details_by_customer_id_serial_number(
        self, customer_id, serial_number
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        # appliance_image_url, sub_category, brand, category, model_number, purchased_from,
        # seller, purchase_date, installation_date, warranty_period, warranty_expiry,

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT category, sub_category, brand, model_number, purchased_from, seller, purchase_date, installation_date, warranty_period, warranty_expiration, appliance_image_url
                FROM customer_appliances
                WHERE customer_id = :customer_id
                AND serial_number = :serial_number
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "customer_id": customer_id,
                    "serial_number": serial_number},
            ).fetchone()

            customer_appliance_details = {
                "category": result[0],
                "sub_category": result[1],
                "brand": result[2],
                "model_number": result[3],
                "serial_number": serial_number,
                "purchased_from": result[4],
                "seller": result[5],
                "purchase_date": result[6],
                "installation_date": result[7],
                "warranty_period": result[8],
                "warranty_expiration": result[9],
                "appliance_image_url": result[10],
            }

            return customer_appliance_details


class QueryCustomers:
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

    def check_customer_exists_by_email(self, email):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                "SELECT EXISTS (SELECT 1 FROM customers WHERE email = :email)"
            )

            result = db_conn.execute(
                query, parameters={
                    "email": email}).fetchone()

            return result[0] == 1

    def fetch_customer_details_by_username(self, username, columns=None):
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

            results_map = {}

            if columns:
                try:
                    for idx, column in enumerate(columns):
                        results_map[column] = result[idx]

                except Exception as error:
                    pass

            else:
                try:
                    results_map = {
                        "customer_id": result[0],
                        "first_name": result[1],
                        "last_name": result[2],
                        "dob": result[3],
                        "gender": result[4],
                        "email": result[5],
                        "phone_number": result[6],
                        "profile_picture": result[7],
                        "street": result[8],
                        "district": result[9],
                        "city": result[10],
                        "state": result[11],
                        "country": result[12],
                        "zip_code": result[13],
                        "created_at": result[14],
                    }

                except Exception as error:
                    pass

            return results_map
        
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


class QueryEngineers:
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

    def check_engineer_exists_by_email(self, email):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                "SELECT EXISTS (SELECT 1 FROM engineers WHERE email = :email)"
            )

            result = db_conn.execute(
                query, parameters={
                    "email": email}).fetchone()

            return result[0] == 1

    def fetch_engineer_details_by_id(self, engineer_id, columns=None):
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

            if columns:
                try:
                    for idx, column in enumerate(columns):
                        results_map[column] = result[idx]

                except Exception as error:
                    pass

            else:
                try:
                    results_map = {
                        "engineer_id": result[0],
                        "first_name": result[1],
                        "last_name": result[2],
                        "email": result[3],
                        "phone_number": result[4],
                        "availability": result[5],
                        "active_tickets": result[6],
                        "street": result[7],
                        "city": result[8],
                        "district": result[9],
                        "state": result[10],
                        "country": result[11],
                        "zip_code": result[12],
                        "specializations": result[13],
                        "skills": result[14],
                        "rating": result[15],
                        "training_id": result[16],
                        "reward_points": result[17],
                        "profile_picture": result[18],
                        "language_proficiency": result[19],
                        "created_on": result[20],
                    }

                except Exception as error:
                    pass

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


class QueryServiceGuides:
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
