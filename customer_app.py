import time
import bleach
import requests
from PIL import Image

import datetime
import dateutil
from datetime import timedelta

import streamlit as st
import streamlit_antd_components as sac
from streamlit_extras.stylable_container import stylable_container

import firebase_admin
from firebase_admin import auth, credentials

from backend.utils.geo_operations import LocationServices
from backend.channels.email_client import TransactionalEmails
from backend.channels.sms_client import NotificationSMS

from database.cloud_sql.queries import (
    Appliances,
    QueryCustomerAppliances,
    QueryCustomers,
    QueryEngineers,
)
from database.cloud_sql.models import CustomerAppliances
from database.cloud_sql.migrations import MigrateCustomers
from database.cloud_storage.document_storage import CustomerRecordsBucket
from database.cloud_storage.multimedia_storage import (
    OnsiteServiceRequestsBucket,
    ProfilePicturesBucket,
)
from database.firebase.firestore import OnsiteServiceRequestCollection


st.set_page_config(
    page_title="LogIQ: Customer App",
    page_icon="assets/logos/logiq_favicon.png",
    initial_sidebar_state="expanded",
    layout="wide",
)

st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 0.2rem;
                    padding-bottom: 1.55rem;
                }
        </style>
        """,
    unsafe_allow_html=True,
)

with open("assets/css/customers.css") as f:
    css = f.read()

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
        #MainMenu  {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        .stMarkdown a {
            text-decoration: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


if "customer_id" not in st.session_state:
    st.session_state.customer_id = None

if "recent_appliance_serial_numbers" not in st.session_state:
    st.session_state.recent_appliance_serial_numbers = []

if "all_customers_service_requests_list" not in st.session_state:
    st.session_state.all_customers_service_requests_list = []

if "customers_service_requests_list" not in st.session_state:
    st.session_state.customers_service_requests_list = []

if "best_appliancs_by_energy_rating" not in st.session_state:
    st.session_state.best_appliancs_by_energy_rating = None

if "customer_appliance_1_details" not in st.session_state:
    st.session_state.customer_appliance_1_details = []

if "customer_appliance_2_details" not in st.session_state:
    st.session_state.customer_appliance_2_details = []

if "customer_appliance_3_details" not in st.session_state:
    st.session_state.customer_appliance_3_details = []

if "customer_appliance_4_details" not in st.session_state:
    st.session_state.customer_appliance_4_details = []

if "customer_appliance_serial_numbers" not in st.session_state:
    st.session_state.customer_appliance_serial_numbers = []

if "cosr_serial_number" not in st.session_state:
    st.session_state.cosr_serial_number = None

if "cosr_service_category" not in st.session_state:
    st.session_state.cosr_service_category = None

if "cosr_request_title" not in st.session_state:
    st.session_state.cosr_request_title = None

if "cosr_request_description" not in st.session_state:
    st.session_state.cosr_request_description = None

if "cosr_phone_number" not in st.session_state:
    st.session_state.cosr_phone_number = None

if "cosr_email" not in st.session_state:
    st.session_state.cosr_email = None

if "cosr_address_street" not in st.session_state:
    st.session_state.cosr_address_street = None

if "cosr_address_city" not in st.session_state:
    st.session_state.cosr_address_city = None

if "cosr_address_state" not in st.session_state:
    st.session_state.cosr_address_state = None

if "cosr_address_zipcode" not in st.session_state:
    st.session_state.cosr_address_zipcode = None

if "ra_category" not in st.session_state:
    st.session_state.ra_category = None

if "ra_sub_category" not in st.session_state:
    st.session_state.ra_sub_category = None

if "ra_brand" not in st.session_state:
    st.session_state.ra_brand = None

if "ra_model_number" not in st.session_state:
    st.session_state.ra_model_number = None

if "ra_serial_number" not in st.session_state:
    st.session_state.ra_serial_number = None

if "ra_purchase_date" not in st.session_state:
    st.session_state.ra_purchase_date = None

if "ra_installation_date" not in st.session_state:
    st.session_state.ra_installation_date = None

if "ra_seller" not in st.session_state:
    st.session_state.ra_seller = None

if "ra_purchased_from" not in st.session_state:
    st.session_state.ra_purchased_from = None

if "ra_available_appliance_categories" not in st.session_state:
    st.session_state.ra_available_appliance_categories = None

if "ra_available_appliance_sub_categories" not in st.session_state:
    st.session_state.ra_available_appliance_sub_categories = None

if "ra_available_appliance_brands" not in st.session_state:
    st.session_state.ra_available_appliance_brands = None

if "ra_available_appliance_model_numbers" not in st.session_state:
    st.session_state.ra_available_appliance_model_numbers = None

if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""

if "customer_email" not in st.session_state:
    st.session_state.customer_email = ""

if "customer_details" not in st.session_state:
    st.session_state.customer_details = ""

if "distinct_appliance_data" not in st.session_state:
    query_appliances = Appliances()
    st.session_state.distinct_appliance_data = (
        query_appliances.fetch_distinct_appliance_data_with_category()
    )


@st.dialog("Manage Account", width="large")
def dialog_manage_account():
    cola, _, colb = st.columns([1, 0.05, 4], vertical_alignment="top")

    with cola:
        st.image(
            "assets/avatars/customers/female8.png",
            use_container_width=True,
        )

    with colb:
        st.write(" ")
        st.markdown(
            f"""
            <H2 class="h2-vsrd-3">
                {st.session_state.customer_details.get('first_name')} {st.session_state.customer_details.get('last_name')}
            </H2>
            Username: {st.session_state.customer_id}
            &nbsp; • &nbsp;Gender: {st.session_state.customer_details.get('gender')}
            &nbsp; • &nbsp;Date of Birth: {st.session_state.customer_details.get('dob').strftime('%B %d, %Y')}
            """,
            unsafe_allow_html=True,
        )

        st.write(" ")
        st.markdown(
            f"""
            ☎️ **Phone:** (+91) {st.session_state.customer_details.get('phone_number')}
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            📧 **Email:** {st.session_state.customer_details.get('email')}
            """,
            unsafe_allow_html=False,
        )

    st.write(" ")
    selected_tab = sac.tabs(
        [
            sac.TabsItem(label="Personal Details"),
            sac.TabsItem(label="Location Details"),
            sac.TabsItem(label="Update Password"),
        ],
        variant="outline",
    )

    if selected_tab == "Personal Details":
        cola, colb = st.columns(2)
        first_name = bleach.clean(
            cola.text_input(
                "First Name", value=st.session_state.customer_details.get("first_name")
            )
        )
        last_name = bleach.clean(
            colb.text_input(
                "Last Name", value=st.session_state.customer_details.get("last_name")
            )
        )

        phone_number = bleach.clean(
            cola.text_input(
                "Phone Number",
                value=st.session_state.customer_details.get("phone_number"),
            )
        )
        email = bleach.clean(
            colb.text_input(
                "Email Id", value=st.session_state.customer_details.get("email")
            )
        )

        profile_picture = st.file_uploader(
            "Profile Picture",
            type=["png", "jpg"],
            accept_multiple_files=False,
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            use_container_width=True,
        ):
            migrate_customers = MigrateCustomers()
            profile_picture_url = None

            with st.spinner("Updating details...", show_time=True):
                if profile_picture:
                    try:
                        profile_pictures_bucket = ProfilePicturesBucket()

                        profile_picture_url = (
                            profile_pictures_bucket.upload_profile_picture(
                                user_type="customers",
                                user_id=st.session_state.customer_id,
                                file=profile_picture,
                            )
                        )

                    except Exception as error:
                        st.warning(
                            "Unable to save profile picture", icon=":material/warning:"
                        )

                    finally:
                        if profile_picture_url:
                            response = migrate_customers.update_customer(
                                username=st.session_state.customer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                                profile_picture=profile_picture_url,
                            )

                        else:
                            response = migrate_customers.update_customer(
                                username=st.session_state.customer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                            )

                else:
                    response = migrate_customers.update_customer(
                        username=st.session_state.customer_id,
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        email=email,
                    )

            if response:
                st.success(
                    "Profile updated succesfully!",
                    icon=":material/check:")

                try:
                    get_customer_details.clear()
                except Exception as error:
                    pass

                st.session_state.customer_details = None

                try:
                    query_customers = QueryCustomers()
                    st.session_state.customer_details = (
                        query_customers.fetch_customer_details_by_username(
                            st.session_state.customer_id,
                        )
                    )

                except Exception as error:
                    pass

                time.sleep(3)
                st.rerun()

            else:
                alert_warning = st.warning(
                    "Unable to update your profile. Please try again later.",
                    icon=":material/warning:",
                )
                time.sleep(3)
                alert_warning.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Discard and Exit",
            use_container_width=True,
            key="_dicard_updates_button_1",
        ):
            st.rerun()

    elif selected_tab == "Location Details":
        cola, colb = st.columns([3, 1])

        street = bleach.clean(
            cola.text_input(
                "Street", value=st.session_state.customer_details.get("street")
            )
        )

        city = bleach.clean(
            colb.text_input(
                "City", value=st.session_state.customer_details.get("city"))
        )

        cola, colb, colc, cold = st.columns(4)

        district = bleach.clean(
            cola.text_input(
                "District", value=st.session_state.customer_details.get("district")
            )
        )

        state = bleach.clean(
            colb.text_input(
                "State", value=st.session_state.customer_details.get("state")
            )
        )

        zip_code = bleach.clean(
            colc.text_input(
                "Zip Code", value=st.session_state.customer_details.get("zip_code")
            )
        )

        country = bleach.clean(
            cold.text_input(
                "Country", value=st.session_state.customer_details.get("country")
            )
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            use_container_width=True,
        ):
            migrate_customers = MigrateCustomers()

            with st.spinner("Updating details...", show_time=True):
                response = migrate_customers.update_customer(
                    username=st.session_state.customer_id,
                    street=street,
                    city=city,
                    district=district,
                    state=state,
                    zip_code=zip_code,
                    country=country,
                )

            if response:
                st.success(
                    "Profile updated succesfully!",
                    icon=":material/check:")

                try:
                    get_customer_details.clear()
                except Exception as error:
                    pass

                st.session_state.customer_details = None

                try:
                    query_customers = QueryCustomers()
                    st.session_state.customer_details = (
                        query_customers.fetch_customer_details_by_username(
                            st.session_state.customer_id,
                        )
                    )

                except Exception as error:
                    pass

                time.sleep(3)
                st.rerun()

            else:
                alert_warning = st.warning(
                    "Unable to update your profile. Please try again later.",
                    icon=":material/warning:",
                )
                time.sleep(3)
                alert_warning.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Discard and Exit",
            use_container_width=True,
            key="_dicard_updates_button_2",
        ):
            st.rerun()

    else:
        sac.alert(
            label="Update Password",
            description="Click on the button below, and we'll send you an email with link to reset your password.",
            color="orange",
            icon=True,
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Send Password Reset Email",
            icon=":material/forward_to_inbox:",
            use_container_width=True,
        ):
            with st.spinner("Processing request...", show_time=True):
                data = {
                    "email": st.session_state.customer_details.get("email"),
                    "requestType": "PASSWORD_RESET",
                }

                response = requests.post(
                    base_url.format(
                        api_key=api_key), json=data)

                if response.status_code == 200:
                    next_steps_message = "We've sent a password reset link to your registered email address. Please check your inbox and follow the instructions to reset your password."

                    sac.alert(
                        label=f"Password Reset Link Sent",
                        description=next_steps_message,
                        color="success",
                        icon=True,
                    )

                else:
                    alert_password_reset_mail_failed = st.error(
                        "We're having trouble sending the password reset email",
                        icon=":material/error:",
                    )

                    time.sleep(2)
                    alert_password_reset_mail_failed.empty()

                    alert_password_reset_mail_failed = st.error(
                        "Kindly double-check your email id and try again.",
                        icon=":material/error:",
                    )

                    time.sleep(2)
                    alert_password_reset_mail_failed.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Exit",
            use_container_width=True,
            key="_dicard_updates_button_2",
        ):
            st.rerun()


@st.dialog("Password Reset", width="small")
def reset_password():
    api_key = st.secrets["FIREBASE_AUTH_WEB_API_KEY"]

    base_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    )

    sac.alert(
        label="Forgot your Password?",
        description="No worries! Enter your email address below, and we'll send you a link to reset your password.",
        color="orange",
        icon=True,
    )

    input_email = bleach.clean(
        st.text_input(
            "Enter your registered email id",
            placeholder="Registered Email Id",
            label_visibility="collapsed",
        )
    )

    if st.button(
        "Send Password Reset Email",
        icon=":material/forward_to_inbox:",
        use_container_width=True,
    ):
        with st.spinner("Processing request...", show_time=True):
            try:
                query_customers = QueryCustomers()
                customer_exists = query_customers.check_customer_exists_by_email(
                    input_email
                )

            except Exception as error:
                customer_exists = None

        if customer_exists:
            data = {
                "email": input_email,
                "requestType": "PASSWORD_RESET",
            }

            response = requests.post(
                base_url.format(
                    api_key=api_key),
                json=data)

            if response.status_code == 200:
                next_steps_message = "We've sent a password reset link to your registered email address. Please check your inbox and follow the instructions to reset your password."

                sac.alert(
                    label=f"Password Reset Link Sent",
                    description=next_steps_message,
                    color="success",
                    icon=True,
                )

            else:
                alert_password_reset_mail_failed = st.error(
                    "We're having trouble sending the password reset email",
                    icon=":material/error:",
                )
                time.sleep(2)
                alert_password_reset_mail_failed.empty()

                alert_password_reset_mail_failed = st.error(
                    "Kindly double-check your email id and try again.",
                    icon=":material/error:",
                )
                time.sleep(2)
                alert_password_reset_mail_failed.empty()

        else:
            st.warning(
                "No customer found with this username. Please check the username and try again.",
                icon=":material/warning:",
            )


@st.dialog("Attribution and Copyright", width="large")
def dialog_attribution():
    sac.alert(
        label=f"Acknowledgments and Fair Use Notice",
        description="Google Cloud credits are provided for this project as part of the Google AI Sprint 2024.<BR> Additionally, various documents including but not limited to service guides and manuals from various companies have been referenced during the development of this project. These materials are used under fair use as this project is intended solely for educational purposes and not for commercial gain.<BR><BR>If you have any questions or concerns, please contact me at thisisashwinraj@gmail.com.",
        color="info",
        icon=True,
    )


@st.dialog("Register New Appliance", width="large")
def register_new_appliance():
    step_register_appliance = sac.steps(
        items=[
            sac.StepsItem(title="Appliance Details"),
            sac.StepsItem(title="Warranty Details"),
            sac.StepsItem(title="Upload Documents"),
        ],
    )

    st.markdown(" ", unsafe_allow_html=True)

    if step_register_appliance == "Appliance Details":
        cola, colb, colc = st.columns(3)

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_appliance_categories(cache=True):
            try:
                st.session_state.ra_available_appliance_categories = list(
                    st.session_state.distinct_appliance_data.keys()
                )

            except Exception as error:
                st.error(error)

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_appliance_sub_categories(category):
            try:
                if st.session_state.distinct_appliance_data.get(category):
                    st.session_state.ra_available_appliance_sub_categories = list(
                        st.session_state.distinct_appliance_data.get(
                            category).keys()
                    )
                else:
                    st.session_state.ra_available_appliance_sub_categories = None

            except Exception as error:
                st.error(error)

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_appliance_brands(sub_category):
            try:
                if st.session_state.distinct_appliance_data.get(
                    st.session_state.ra_category
                ) and st.session_state.distinct_appliance_data.get(
                    st.session_state.ra_category
                ).get(
                    sub_category
                ):
                    st.session_state.ra_available_appliance_brands = list(
                        st.session_state.distinct_appliance_data.get(
                            st.session_state.ra_category
                        )
                        .get(sub_category)
                        .keys()
                    )
                else:
                    st.session_state.ra_available_appliance_brands = None

            except Exception as error:
                st.error(error)

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_model_numbers(brand, sub_category):
            try:
                if (
                    st.session_state.distinct_appliance_data.get(
                        st.session_state.ra_category
                    )
                    and st.session_state.distinct_appliance_data.get(
                        st.session_state.ra_category
                    ).get(sub_category)
                    and st.session_state.distinct_appliance_data.get(
                        st.session_state.ra_category
                    )
                    .get(st.session_state.ra_sub_category)
                    .get(brand)
                ):
                    st.session_state.ra_available_appliance_model_numbers = list(
                        st.session_state.distinct_appliance_data.get(
                            st.session_state.ra_category
                        )
                        .get(st.session_state.ra_sub_category)
                        .get(brand)
                    )
                else:
                    st.session_state.ra_available_appliance_model_numbers = None

            except Exception as error:
                st.error(error)

        with cola:
            fetch_and_cache_appliance_categories(cache=True)

            try:
                st.session_state.ra_category = st.selectbox(
                    "Appliance Category",
                    st.session_state.distinct_appliance_data.keys(),
                    placeholder="Appliance Category",
                    index=st.session_state.ra_available_appliance_categories.index(
                        st.session_state.ra_category
                    ),
                )

            except Exception as error:
                st.session_state.ra_category = st.selectbox(
                    "Appliance Category",
                    st.session_state.distinct_appliance_data.keys(),
                    placeholder="Appliance Category",
                    index=None,
                )

        with colb:
            fetch_and_cache_appliance_sub_categories(
                st.session_state.ra_category)

            try:
                st.session_state.ra_sub_category = st.selectbox(
                    "Appliance Sub-Category",
                    st.session_state.distinct_appliance_data.get(
                        st.session_state.ra_category
                    ).keys(),
                    placeholder="Appliance Sub-Category",
                    index=st.session_state.ra_available_appliance_sub_categories.index(
                        st.session_state.ra_sub_category
                    ),
                )

            except BaseException:
                st.session_state.ra_sub_category = st.selectbox(
                    "Appliance Sub-Category",
                    st.session_state.ra_available_appliance_sub_categories,
                    placeholder="Appliance Sub-Category",
                    index=None,
                )

        with colc:
            fetch_and_cache_appliance_brands(st.session_state.ra_sub_category)

            try:
                st.session_state.ra_brand = st.selectbox(
                    "Appliance Brand",
                    st.session_state.ra_available_appliance_brands,
                    placeholder="Appliance Brand",
                    index=st.session_state.ra_available_appliance_brands.index(
                        st.session_state.ra_brand
                    ),
                )

            except BaseException:
                st.session_state.ra_brand = st.selectbox(
                    "Appliance Brand",
                    st.session_state.ra_available_appliance_brands,
                    placeholder="Appliance Brand",
                    index=None,
                )

        st.info(
            "Serial number is located on the back or underside of your appliance",
            icon=":material/info:",
        )

        cola, colb = st.columns(2)

        with cola:
            fetch_and_cache_model_numbers(
                st.session_state.ra_brand, st.session_state.ra_sub_category
            )

            try:
                st.session_state.ra_model_number = st.selectbox(
                    "Model Number",
                    st.session_state.ra_available_appliance_model_numbers,
                    placeholder="Model Number",
                    index=st.session_state.ra_available_appliance_model_numbers.index(
                        st.session_state.ra_model_number
                    ),
                )

            except BaseException:
                st.session_state.ra_model_number = st.selectbox(
                    "Model Number",
                    st.session_state.ra_available_appliance_model_numbers,
                    placeholder="Model Number",
                    index=None,
                )

        with colb:
            st.session_state.ra_serial_number = st.text_input(
                    "Serial Number",
                    placeholder="Serial Number",
                    value=st.session_state.ra_serial_number,
                )
            
            if st.session_state.ra_serial_number:
                st.session_state.ra_serial_number = bleach.clean(
                    st.session_state.ra_serial_number
                )

    elif step_register_appliance == "Warranty Details":
        cola, colb = st.columns(2)

        with cola:
            st.session_state.ra_purchase_date = st.date_input(
                "Purchase Date",
                (
                    st.session_state.ra_purchase_date
                    if st.session_state.ra_purchase_date is not None
                    else datetime.datetime.today()
                ),
                max_value=datetime.datetime.today(),
                format="YYYY-MM-DD",
            )

        with colb:
            st.session_state.ra_installation_date = st.date_input(
                "Installation Date",
                (
                    st.session_state.ra_installation_date
                    if st.session_state.ra_installation_date is not None
                    else datetime.datetime.today()
                ),
                max_value=datetime.datetime.today(),
                format="YYYY-MM-DD",
            )

        st.info(
            "Seller details and purchase info can be found on the product invoice",
            icon=":material/info:",
        )
        cola, colb = st.columns(2)

        with cola:
            st.session_state.ra_purchased_from = st.text_input(
                    "Purchased From",
                    placeholder="Purchased From",
                    value=st.session_state.ra_purchased_from,
                )

            if st.session_state.ra_purchased_from:
                st.session_state.ra_purchased_from = bleach.clean(
                    st.session_state.ra_purchased_from
                )

        with colb:
            st.session_state.ra_seller = st.text_input(
                    "Seller",
                    placeholder="Seller",
                    value=st.session_state.ra_seller,
                )

            if st.session_state.ra_seller:
                st.session_state.ra_seller = bleach.clean(
                    st.session_state.ra_seller
                )

    else:
        ra_purchase_invoice_file = st.file_uploader(
            "Upload Your Purchase Invoice",
            type=["pdf"],
            accept_multiple_files=False,
        )

        ra_warranty_certificate_file = st.file_uploader(
            "Upload Warranty Certificate",
            type=["pdf"],
            accept_multiple_files=False,
        )

        if st.button("Submit Details and Register Appliance",
                     icon=":material/check:"):
            progress_bar = st.progress(
                0, text="Verifying the registration form fields")

            if (
                (st.session_state.ra_category is None)
                or (st.session_state.ra_sub_category is None)
                or (st.session_state.ra_brand is None)
                or (st.session_state.ra_model_number is None)
                or (st.session_state.ra_serial_number is None)
            ):
                warning_status = st.warning(
                    "Kindly fill the missing fields in Step 1 - Appliance Details",
                    icon=":material/warning:",
                )

                time.sleep(3)
                warning_status.empty()

            elif (
                (st.session_state.ra_purchase_date is None)
                or (st.session_state.ra_installation_date is None)
                or (st.session_state.ra_purchased_from is None)
                or (st.session_state.ra_seller is None)
            ):
                warning_status = st.warning(
                    "Kindly fill the missing fields in Step 2 - Warranty Details",
                    icon=":material/warning:",
                )

                time.sleep(3)
                warning_status.empty()

            elif (ra_purchase_invoice_file is None) or (
                ra_warranty_certificate_file is None
            ):
                warning_status = st.warning(
                    "Kindly upload the missing documents in Step 3 - Upload Documents",
                    icon=":material/warning:",
                )

                time.sleep(3)
                warning_status.empty()

            else:
                customer_records_bucket = CustomerRecordsBucket()
                flag_appliance_registration_status = True

                progress_bar.progress(
                    25, "Saving appliance details and uploading documents"
                )

                try:
                    # Upload Invoice to blob
                    uploaded_purchase_invoice_to_bucket = (
                        customer_records_bucket.upload_purchase_invoice(
                            customer_id=st.session_state.customer_id,
                            serial_number=st.session_state.ra_serial_number,
                            sub_category=st.session_state.ra_sub_category,
                            file=ra_purchase_invoice_file,
                        )
                    )

                    progress_bar.progress(
                        50, "Registering your appliance warranty")

                except Exception as error:
                    uploaded_purchase_invoice_to_bucket = False
                    flag_appliance_registration_status = False

                try:
                    # Upload Warranty to blob
                    uploaded_warranty_certificate_to_bucket = (
                        customer_records_bucket.upload_warranty_certificate(
                            customer_id=st.session_state.customer_id,
                            serial_number=st.session_state.ra_serial_number,
                            sub_category=st.session_state.ra_sub_category,
                            file=ra_warranty_certificate_file,
                        )
                    )

                    progress_bar.progress(75, "Adding device to your profile")

                except Exception as error:
                    uploaded_warranty_certificate_to_bucket = False
                    flag_appliance_registration_status = False

                # Store data in cloud sql
                if (
                    uploaded_purchase_invoice_to_bucket
                    and uploaded_warranty_certificate_to_bucket
                ):
                    query_appliances = Appliances()
                    model_customer_appliances = CustomerAppliances()

                    try:
                        warranty_period_in_months, appliance_image_gcs_url = (
                            query_appliances.fetch_warranty_period_and_appliance_image_url_by_brand_sub_category_and_model_number(
                                brand=st.session_state.ra_brand,
                                sub_category=st.session_state.ra_sub_category,
                                model_number=st.session_state.ra_model_number,
                            )
                        )

                        warranty_expiration_date = (
                            st.session_state.ra_installation_date
                            + dateutil.relativedelta.relativedelta(
                                months=int(warranty_period_in_months)
                            )
                        ).strftime("%Y-%m-%d")

                        store_customer_appliance_details_to_cloudsql = (
                            model_customer_appliances.add_customer_appliance(
                                customer_id=st.session_state.customer_id,
                                category=st.session_state.ra_category,
                                sub_category=st.session_state.ra_sub_category,
                                brand=st.session_state.ra_brand,
                                model_number=st.session_state.ra_model_number,
                                serial_number=st.session_state.ra_serial_number,
                                purchase_date=st.session_state.ra_purchase_date,
                                warranty_period=warranty_period_in_months,
                                warranty_expiration=warranty_expiration_date,
                                purchased_from=st.session_state.ra_purchased_from,
                                seller=st.session_state.ra_seller,
                                installation_date=st.session_state.ra_installation_date,
                                appliance_image_url=appliance_image_gcs_url,
                            )
                        )

                        progress_bar.progress(
                            100, "Your appliance has been registered."
                        )

                    except Exception as error:
                        flag_appliance_registration_status = False

                if flag_appliance_registration_status == True:
                    try:
                        fetch_and_cache_customer_appliance_details.clear()

                    except Exception as error:
                        pass

                    del st.session_state.ra_sub_category
                    del st.session_state.ra_brand
                    del st.session_state.ra_model_number
                    del st.session_state.ra_serial_number

                    del st.session_state.ra_purchase_date
                    del st.session_state.ra_purchased_from
                    del st.session_state.ra_seller
                    del st.session_state.ra_installation_date

                    del ra_purchase_invoice_file
                    del ra_warranty_certificate_file

                    del st.session_state.ra_available_appliance_categories
                    del st.session_state.ra_available_appliance_sub_categories
                    del st.session_state.ra_available_appliance_brands
                    del st.session_state.ra_available_appliance_model_numbers

                    # Display status to users
                    success_status = st.success(
                        "Congratulations! Your new appliance has been registered.",
                        icon="🎉",
                    )
                    time.sleep(3)
                    success_status.empty()
                    st.rerun()

                else:
                    failure_status = st.error(
                        "Oops! We're facing some trouble connecting. Try again later",
                        icon="🚨",
                    )
                    time.sleep(3)
                    failure_status.empty()
                    st.rerun()


@st.dialog("Appliance Details", width="large")
def view_customer_appliance_details(appliance_details):
    cola, _, colb = st.columns([5, 0.3, 8])

    with cola:
        st.image(
            appliance_details["appliance_image_url"],
            use_container_width=True,
        )

    with colb:
        st.markdown(
            f"<H2>{
                appliance_details['sub_category']}</H2>{
                appliance_details['brand']} {
                appliance_details['category']} • Model No.: {
                    appliance_details['model_number']}<BR>Purchased from {
                        appliance_details['purchased_from']} ({
                            appliance_details['seller']})",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<BR>📅 <B>Purchased On:</B> {
                appliance_details['purchase_date']}&nbsp;&nbsp; 📅 <B>Installed On:</B> {
                appliance_details['installation_date']}<BR>✅ {
                appliance_details['warranty_period']}-Month Manufacturer Warranty, Expires on {
                    appliance_details['warranty_expiration']}",
            unsafe_allow_html=True,
        )
        st.markdown("", unsafe_allow_html=True)

        colx, coly = st.columns(2)
        customer_records_bucket = CustomerRecordsBucket()

        product_invoice_url = customer_records_bucket.fetch_product_invoice_url(
            customer_id=st.session_state.customer_id,
            serial_number=appliance_details["serial_number"],
            sub_category=appliance_details["sub_category"],
        )

        warranty_certificate_url = (
            customer_records_bucket.fetch_warranty_certificate_url(
                customer_id=st.session_state.customer_id,
                serial_number=appliance_details["serial_number"],
                sub_category=appliance_details["sub_category"],
            )
        )

        with colx:
            st.link_button(
                "Product Invoice",
                url=product_invoice_url,
                use_container_width=True,
                icon=":material/receipt_long:",
            )

        with coly:
            st.link_button(
                "Warranty Certificate",
                url=warranty_certificate_url,
                use_container_width=True,
                icon=":material/description:",
            )


@st.dialog("Create New Onsite Service Request", width="large")
def create_new_onsite_service_request():
    step_register_service_request = sac.steps(
        items=[
            sac.StepsItem(title="Service Request Details"),
            sac.StepsItem(title="Address and Attachments"),
        ],
    )
    st.markdown(" ", unsafe_allow_html=True)

    @st.cache_data(show_spinner=False)
    def fetch_and_cache_customer_appliance_serials(cache=True):
        query_customer_appliances = QueryCustomerAppliances()

        st.session_state.customer_appliance_serial_numbers = (
            query_customer_appliances.fetch_appliance_serial_numbers_by_customer_id(
                customer_id=st.session_state.customer_id, limit=-1
            )
        )

    fetch_and_cache_customer_appliance_serials(cache=True)

    if step_register_service_request == "Service Request Details":
        cola, colb = st.columns(2)

        with cola:
            try:
                st.session_state.cosr_serial_number = st.selectbox(
                    "Serial Number",
                    st.session_state.customer_appliance_serial_numbers,
                    placeholder="12-Digit Serial Number",
                    index=st.session_state.customer_appliance_serial_numbers.index(
                        st.session_state.cosr_serial_number
                    ),
                )

            except Exception as error:
                st.session_state.cosr_serial_number = st.selectbox(
                    "Serial Number",
                    st.session_state.customer_appliance_serial_numbers,
                    placeholder="12-Digit Serial Number",
                    index=None,
                )

        available_onsite_service_categories = [
            "Installation",
            "Maintenance/Servicing",
            "Calibration",
            "Part Replacement",
            "Noise/Leakage Issue",
            "Software/Firmware Update",
            "Inspection and Diagnosis",
            "Wiring Inspection",
            "Electrical Malfunction",
            "Mechanical Repair",
            "Overheating",
            "General Appliance Troubleshooting",
            "Cooling/Heating Issue",
            "Water Drainage Problem",
            "Vibration/Imbalance",
            "Gas Leakage Detection" "Rust or Corrosion Repair",
            "Control Panel Malfunction",
            "Error Code Diagnosis",
            "Appliance Relocation Assistance",
            "Smart Home Integration Support",
        ]

        with colb:
            try:
                st.session_state.cosr_service_category = st.selectbox(
                    "Service Category",
                    available_onsite_service_categories,
                    placeholder="Select the Service Category",
                    index=available_onsite_service_categories.index(
                        st.session_state.cosr_service_category
                    ),
                )

            except Exception as error:
                st.session_state.cosr_service_category = st.selectbox(
                    "Service Category",
                    available_onsite_service_categories,
                    placeholder="Service Category",
                    index=None,
                )

        st.session_state.cosr_request_title = st.text_input(
                "Request Title",
                placeholder="Enter a Suitable Title",
                value=st.session_state.cosr_request_title,
            )

        if st.session_state.cosr_request_title:
            st.session_state.cosr_request_title = bleach.clean(
                st.session_state.cosr_request_title
            )

        st.session_state.cosr_request_description = st.text_area(
            "Issue Description",
            placeholder="Briefly describe your issue in min 30 words",
            value=st.session_state.cosr_request_description,
        )

        if st.session_state.cosr_request_description:
            st.session_state.cosr_request_description = bleach.clean(
                st.session_state.cosr_request_description
            )

        if st.session_state.cosr_request_description:
            if len(st.session_state.cosr_request_description.split()) < 30:
                st.warning(
                    "Please desribe the issue in atleast 30 words",
                    icon="⚠️")

    elif step_register_service_request == "Address and Attachments":
        cola, colb = st.columns(2)

        with cola:
            st.session_state.cosr_phone_number = st.text_input(
                    "Phone Number",
                    placeholder="Enter your Phone Number",
                    value=st.session_state.cosr_phone_number,
                )

            if st.session_state.cosr_phone_number:
                st.session_state.cosr_phone_number = bleach.clean(
                    st.session_state.cosr_phone_number
                )

        with colb:
            st.session_state.cosr_email = st.text_input(
                    "E Mail",
                    placeholder="E Mail",
                    value=st.session_state.cosr_email,
                )

            if st.session_state.cosr_email:
                st.session_state.cosr_email = bleach.clean(
                    st.session_state.cosr_email
                )

        st.session_state.cosr_address_street = st.text_input(
            "Street/Apartment No.",
            placeholder="Enter your street address, include landmarks",
            value=st.session_state.cosr_address_street,
        )

        if st.session_state.cosr_address_street:
            st.session_state.cosr_address_street = bleach.clean(
                st.session_state.cosr_address_street
            )

        colx, coly, colz = st.columns(3)

        with colx:
            st.session_state.cosr_address_zipcode = st.text_input(
                    "Zipcode",
                    placeholder="Zipcode",
                    value=st.session_state.cosr_address_zipcode,
                )

            if st.session_state.cosr_address_zipcode:
                st.session_state.cosr_address_zipcode = bleach.clean(
                    st.session_state.cosr_address_zipcode
                )

            if (
                (st.session_state.cosr_address_zipcode is not None)
                and (
                    st.session_state.cosr_address_city is None
                    or st.session_state.cosr_address_city == ""
                )
                and (
                    st.session_state.cosr_address_state is None
                    or st.session_state.cosr_address_state == ""
                )
            ):
                location_services = LocationServices()

                (
                    st.session_state.cosr_address_city,
                    st.session_state.cosr_address_state,
                ) = location_services.get_city_and_state_from_zipcode(
                    zipcode=st.session_state.cosr_address_zipcode
                )

        with coly:
            st.session_state.cosr_address_city = st.text_input(
                    "City",
                    placeholder="City",
                    value=st.session_state.cosr_address_city,
                )
            
            if st.session_state.cosr_address_city:
                st.session_state.cosr_address_city = bleach.clean(
                    st.session_state.cosr_address_city
                )

        with colz:
            st.session_state.cosr_address_state = st.text_input(
                    "State",
                    placeholder="State",
                    value=st.session_state.cosr_address_state,
                )
            
            if st.session_state.cosr_address_state:
                st.session_state.cosr_address_state = bleach.clean(
                    st.session_state.cosr_address_state
                )

        cosr_attachments = st.file_uploader(
            "Upload image references",
            type=["png", "jpg", "pdf"],
            accept_multiple_files=True,
        )

        if st.button("Raise New Service Request",
                     icon=":material/library_add:"):
            try:
                progress_bar = st.progress(
                    0, text="Preparing to process your request")
                query_customer_appliances = QueryCustomerAppliances()

                progress_bar.progress(20, "Validating customer information")

                appliance_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                    customer_id=st.session_state.customer_id,
                    serial_number=st.session_state.cosr_serial_number,
                )
                progress_bar.progress(40, "Verifying service request details")

                service_request_data = {
                    "city": st.session_state.cosr_address_city,
                    "state": st.session_state.cosr_address_state,
                    "street": st.session_state.cosr_address_street,
                    "zipcode": st.session_state.cosr_address_zipcode,
                    "category": appliance_details["category"],
                    "sub_category": appliance_details["sub_category"],
                    "brand": appliance_details["brand"],
                    "model_number": appliance_details["model_number"],
                    "serial_number": appliance_details["serial_number"],
                    "purchased_from": appliance_details["purchased_from"],
                    "seller": appliance_details["seller"],
                    "purchase_date": appliance_details["purchase_date"].strftime(
                        "%Y-%m-%d"
                    ),
                    "installation_date": appliance_details[
                        "installation_date"
                    ].strftime("%Y-%m-%d"),
                    "warranty_period": appliance_details["warranty_period"],
                    "warranty_expiration": appliance_details[
                        "warranty_expiration"
                    ].strftime("%Y-%m-%d"),
                    "appliance_image_url": appliance_details["appliance_image_url"],
                    "phone_number": st.session_state.cosr_phone_number,
                    "email": st.session_state.cosr_email,
                    "description": st.session_state.cosr_request_description,
                    "request_title": st.session_state.cosr_request_title,
                    "request_type": st.session_state.cosr_service_category,
                }

                onsite_service_request_collection_firestore = (
                    OnsiteServiceRequestCollection()
                )

                service_request_id = onsite_service_request_collection_firestore.create_onsite_service_request(
                    customer_id=st.session_state.customer_id,
                    service_request_data=service_request_data,
                )

                progress_bar.progress(
                    60, "Updating our system with your request")

                try:
                    if cosr_attachments:
                        onsite_service_requests_bucket = OnsiteServiceRequestsBucket()

                        for attachment in cosr_attachments:
                            onsite_service_requests_bucket.upload_customer_attachment(
                                request_id=service_request_id,
                                image_file=attachment,
                                image_filename=attachment.name,
                            )

                        progress_bar.progress(
                            80, "Finalizing your service request")

                except Exception as error:
                    st.warning(
                        "Uh-oh! Could not save the attachments.", icon="⚠️")
                    time.sleep(2)

                engineer_assignment_cloud_run_payload = {
                    "customer_id": str(st.session_state.customer_id),
                    "request_id": str(service_request_id),
                }

                response = requests.post(
                    str(st.secrets["URL_CLOUD_RUN_ONSITE_ENGINEER_ASSIGNMENT_SERVICE"]),
                    json=engineer_assignment_cloud_run_payload,
                )

                if response.status_code != 200:
                    try:
                        onsite_service_request_collection = (
                            OnsiteServiceRequestCollection()
                        )
                        onsite_service_request_collection.update_engineer_for_service_request(
                            str(st.session_state.customer_id),
                            service_request_id,
                            "ADMIN",
                        )
                    except Exception as error:
                        pass

                try:
                    transaction_email_channel = TransactionalEmails()

                    transaction_email_channel.send_onsite_service_request_confirmation_mail(
                        receiver_full_name=st.session_state.customer_name,
                        receiver_email=st.session_state.st.session_state.cosr_email,
                        service_request_id=service_request_id,
                    )

                except Exception as error:
                    pass

                try:
                    notification_sms_channel = NotificationSMS()

                    notification_sms_channel.send_onsite_service_request_confirmation_sms(
                        receivers_phone_number=st.session_state.cosr_phone_number,
                        service_request_id=service_request_id,
                    )

                except Exception as error:
                    pass

                st.session_state.cosr_serial_number = None
                st.session_state.cosr_service_category = None
                st.session_state.cosr_service_category = None
                st.session_state.cosr_request_title = None
                st.session_state.cosr_request_description = None
                st.session_state.cosr_phone_number = None
                st.session_state.cosr_email = None
                st.session_state.cosr_address_street = None
                st.session_state.cosr_address_city = None
                st.session_state.cosr_address_state = None
                st.session_state.cosr_address_zipcode = None

                del st.session_state.customer_appliances

                try:
                    fetch_and_cache_customers_service_requests.clear()
                except Exception as error:
                    pass

                progress_bar.progress(
                    100, "Service request created succesfully")

                st.success(
                    f"Your service request has been created with id: {service_request_id}",
                    icon=":material/check:",
                )

                time.sleep(3)
                st.rerun()

            except Exception as error:
                st.error(
                    "Oops! We're facing some trouble connecting. Try again later",
                    icon=":material/error:",
                )

                time.sleep(3)
                st.rerun()


@st.dialog("Service Request Details", width="large")
def view_service_request_details(service_request_id, service_request_details):
    if service_request_details.get("assignment_status").lower() == "confirmed":
        assigned_to_engineer_id = service_request_details.get("assigned_to")

        @st.cache_data(show_spinner=False)
        def get_engineer_name(assigned_to_engineer_id):
            query_engineers = QueryEngineers()
            engineer_name_details = query_engineers.fetch_engineer_details_by_id(
                assigned_to_engineer_id,
                ["first_name", "last_name"],
            )

            engineer_name = f"""
                {engineer_name_details.get('first_name')}
                {engineer_name_details.get('last_name')}
                """

            return engineer_name

        engineer_name = get_engineer_name(assigned_to_engineer_id)

    cola, colb = st.columns([2, 1])

    with cola:
        st.markdown(
            f"""
            <P class="p-vsrd-1">Request Id: {service_request_id}</P><H1 class="h1-vsrd-1">{service_request_details.get('request_title')}</H1>
            """,
            unsafe_allow_html=True,
        )

    with colb:
        st.markdown(
            f"""
            <H2 class="h2-vsrd-2" align='right'>
                <B>Status: {service_request_details.get('ticket_status').capitalize()}</B>
            </P>
            """,
            unsafe_allow_html=True,
        )

    cola, _, colb = st.columns([1, 0.1, 4])

    with cola:
        st.image(
            service_request_details.get(
                "appliance_details").get("appliance_image_url"),
            use_container_width=True,
        )

    with colb:
        st.markdown(
            f"""
            <H2 class="h2-vsrd-1">
                {service_request_details.get('appliance_details').get('sub_category')}
            </H2>
            {service_request_details.get('appliance_details').get('brand')} {service_request_details.get('appliance_details').get('category')} •
            Model No.: {service_request_details.get('appliance_details').get('model_number')}
            """,
            unsafe_allow_html=True,
        )

        st.write(" ")
        request_created_on = datetime.datetime.strptime(
            service_request_details.get("created_on"),
            "%Y-%m-%d %H:%M:%S",
        )

        if service_request_details.get(
                "assignment_status").lower() == "confirmed":
            st.markdown(
                f"""
                📅 Request Created On: {request_created_on.strftime('%B %d, %Y (%A)')}
                <BR>
                ✅ Engineer {engineer_name} (Id: {assigned_to_engineer_id}) assigned to your request
                """,
                unsafe_allow_html=True,
            )

        else:
            st.markdown(
                f"""
                📅 Request Created On: {request_created_on.strftime('%B %d, %Y (%A)')}
                <BR>
                ⚠️ We will notify you when an engineer is assigned to your request
                """,
                unsafe_allow_html=True,
            )

    st.write(" ")

    if service_request_details.get("ticket_status").lower() == "resolved":
        selected_tab = sac.tabs(
            [
                sac.TabsItem(label="Request Details"),
                sac.TabsItem(label="Appliance Details"),
                sac.TabsItem(label="Ticket Activity"),
            ],
            variant="outline",
        )

    else:
        selected_tab = sac.tabs(
            [
                sac.TabsItem(label="Request Details"),
                sac.TabsItem(label="Appliance Details"),
                sac.TabsItem(label="Ticket Activity"),
                sac.TabsItem(label="Generate OTP"),
            ],
            variant="outline",
        )

    if selected_tab == "Request Details":
        colx, coly = st.columns([3, 1.5])

        with colx:
            st.markdown(
                f"🈺 <B>Request Type:</B> {
                    service_request_details.get('request_type')}",
                unsafe_allow_html=True,
            )

        with coly:
            st.markdown(
                f"<P align='right'>📆 <B>Serial No.:</B> {
                    service_request_details.get('appliance_details').get('serial_number')}</P>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<P align='justify'>▶️ <B>Request Description:</B><BR>{
                service_request_details.get('description')}</P>",
            unsafe_allow_html=True,
        )

    elif selected_tab == "Appliance Details":
        st.markdown(
            f"📛 <B>Appliance Name:</B> {
                service_request_details.get('appliance_details').get('brand')} {
                service_request_details.get('appliance_details').get('sub_category')}",
            unsafe_allow_html=True,
        )

        cola, colb, colc = st.columns([1.1, 1.1, 1])

        with cola:
            st.markdown(
                f"🔢 <B>Serial Number:</B> {
                    service_request_details.get('appliance_details').get('serial_number')}",
                unsafe_allow_html=True,
            )

        with colb:
            st.markdown(
                f"🏷️ <B>Model Number:</B> {
                    service_request_details.get('appliance_details').get('model_number')}",
                unsafe_allow_html=True,
            )

        with colc:
            st.markdown(
                f"📆 <B>Purchased On:</B> {
                    service_request_details.get('appliance_details').get('purchase_date')}",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"✅ {
                service_request_details.get('appliance_details').get('warranty_period')}-Month Manufacturer Warranty, Expires on {
                service_request_details.get('appliance_details').get('warranty_expiration')} (Purchased from {
                service_request_details.get('appliance_details').get('seller')})",
            unsafe_allow_html=True,
        )

        customer_records_bucket = CustomerRecordsBucket()
        cola, colb, _ = st.columns([1.4, 0.3, 1.7])

        with cola:
            warranty_certificate_url = (
                customer_records_bucket.fetch_warranty_certificate_url(
                    customer_id=st.session_state.customer_id,
                    serial_number=service_request_details.get("appliance_details").get(
                        "serial_number"
                    ),
                    sub_category=service_request_details.get("appliance_details").get(
                        "sub_category"
                    ),
                )
            )

            st.link_button(
                "Download Warranty Certificate",
                url=warranty_certificate_url,
                use_container_width=True,
                icon=":material/download:",
            )

        with colb:
            product_invoice_url = customer_records_bucket.fetch_product_invoice_url(
                customer_id=st.session_state.customer_id,
                serial_number=service_request_details.get("appliance_details").get(
                    "serial_number"
                ),
                sub_category=service_request_details.get("appliance_details").get(
                    "sub_category"
                ),
            )

            st.link_button(
                "",
                icon=":material/receipt_long:",
                help="Product Invoice",
                url=product_invoice_url,
                use_container_width=True,
            )

    elif selected_tab == "Ticket Activity":
        cola, colb = st.columns([5, 1], vertical_alignment="bottom")

        with cola:
            st.text_area(
                "Enter customer notes",
                placeholder="Share new update to post...",
                label_visibility="collapsed",
                height=80,
            )

        with colb:
            st.button("Post Update", use_container_width=True)

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_ticket_activity(customer_id, request_id):
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            return onsite_service_request_collection.fetch_service_request_activity(
                customer_id, request_id
            )

        ticket_activity = fetch_and_cache_ticket_activity(
            st.session_state.customer_id,
            service_request_id,
        )

        for activity in ticket_activity:
            added_by = activity.get("added_by")

            if added_by.lower() == "admin":
                added_by = "Admin"
                color = "pink"
            elif added_by.lower() == "engineer":
                added_by = "Engineer"
                color = "green"
            elif added_by.lower() == "customer":
                added_by = "Customer"
                color = "blue"
            else:
                added_by = "System"
                color = "yellow"

            timestamp = datetime.datetime.strptime(
                activity.get("timestamp"), "%Y-%m-%d %H:%M:%S"
            ).strftime("%B %d, %Y (%H:%M Hrs)")

            sac.alert(
                label=f"{added_by} - {timestamp}",
                description=activity.get("notes"),
                variant="quote",
                color=color,
                icon=False,
                key=activity.get("timestamp"),
            )

    else:
        resolution_start_date = service_request_details.get("resolution").get(
            "start_date"
        )
        onsite_service_request_collection = OnsiteServiceRequestCollection()

        if resolution_start_date == "":
            otp_alert = sac.alert(
                label=f"Generate OTP for Engineer Verification",
                description="Please generate a One-Time Password (OTP) to verify the engineer when they arrive at your location. This OTP will be used to confirm the engineer's identity and authorize them to proceed with the repair or service.",
                color="orange",
                icon=True,
            )

            if st.button(
                "Generate Engineer Verification OTP",
                icon=":material/policy:",
            ):
                otp = onsite_service_request_collection.generate_engineer_verification_otp(
                    customer_id=st.session_state.customer_id,
                    request_id=service_request_id,
                )

                st.success(
                    f"Your One-Time Password (OTP) for Engineer Verification is {otp}",
                    icon=":material/lock_clock:",
                )
                del otp_alert

        else:
            otp_alert = sac.alert(
                label=f"Verify Service Completion and Generate Invoice",
                description="Before closing the ticket, please verify that all requested services have been completed to your satisfaction. Once confirmed, share the final One-Time Password (OTP) with the engineer to mark the ticket as resolved.",
                color="orange",
                icon=True,
            )

            if st.button(
                "Generate Resolution Completion OTP",
                icon=":material/policy:",
            ):
                otp = onsite_service_request_collection.generate_resolution_verification_otp(
                    customer_id=st.session_state.customer_id,
                    request_id=service_request_id,
                )

                st.success(
                    f"Your One-Time Password (OTP) for Resolution Completion is {otp}",
                    icon=":material/lock_clock:",
                )
                del otp_alert


@st.dialog("Edit Request Details", width="large")
def edit_service_request_details(service_request_id, service_request_details):
    cola, colb = st.columns(2)

    with cola:
        updated_request_title = bleach.clean(
            st.text_input(
                "Request Title", value=service_request_details.get("request_title")
            )
        )

    with colb:
        bleach.clean(
            st.text_input(
                "Request Type",
                value=service_request_details.get("request_type"),
                disabled=True,
            )
        )

    updated_description = st.text_area(
        "Description", value=service_request_details.get("description")
    )

    cola, colb, _ = st.columns([5, 1.2, 8])

    with cola:
        button_update_service_request = st.button(
            "Update Request Details",
            icon=":material/update:",
            use_container_width=True,
        )

    with colb:
        button_delete_service_request = st.button(
            "",
            icon=":material/cancel:",
            use_container_width=True,
        )

    if button_update_service_request:
        onsite_service_request_collection = OnsiteServiceRequestCollection()

        edit_service_request = onsite_service_request_collection.update_title_and_description_for_service_request(
            customer_id=st.session_state.customer_id,
            service_request_id=service_request_id,
            updated_request_title=updated_request_title,
            updated_description=updated_description,
        )

        if edit_service_request:
            st.success(
                "Your service request has been updated.",
                icon=":material/check:",
            )

            try:
                fetch_and_cache_customers_service_requests.clear()
            except Exception as error:
                pass

            time.sleep(3)
            st.rerun()

        else:
            st.error(
                "Oops! We're facing some trouble connecting. Try again later",
                icon=":material/error:",
            )

            time.sleep(3)
            st.rerun()

    if button_delete_service_request:
        st.rerun()


@st.cache_data(show_spinner=False, ttl="30 minutes")
def get_greetings(is_ist):
    morning_start = timedelta(hours=5)
    afternoon_start = timedelta(hours=12)
    evening_start = timedelta(hours=17)
    night_start = timedelta(hours=21)

    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)

    current_time = timedelta(hours=ist_now.hour, minutes=ist_now.minute)

    if morning_start <= current_time < afternoon_start:
        greeting = "Good Morning"
    elif afternoon_start <= current_time < evening_start:
        greeting = "Good Afternoon"
    elif evening_start <= current_time < night_start:
        greeting = "Good Evening"
    else:
        greeting = "Hello"

    return greeting


@st.cache_data(show_spinner=False)
def get_customer_details(full_name=True):
    query_customers = QueryCustomers()

    customer_details = query_customers.fetch_customer_details_by_username(
        st.session_state.customer_id,
    )

    st.session_state.customer_details = customer_details

    try:
        if full_name:
            st.session_state.customer_name = (
                customer_details.get("first_name")
                + " "
                + customer_details.get("last_name")
            )
        else:
            st.session_state.customer_name = customer_details.get("first_name")

    except Exception as error:
        st.session_state.customer_name = "LogIQ User"

    return st.session_state.customer_name


if "themes" not in st.session_state:
    st.session_state.themes = {
        "current_theme": "light",
        "refreshed": True,
        "light": {
            "theme.base": "dark",
            "theme.backgroundColor": "#111111",
            "theme.primaryColor": "#64ABD8",
            "theme.secondaryBackgroundColor": "#181818",
            "theme.textColor": "#EAE9FC",
            "containerColor": "#f0f2f6",
            "containerBoundaryColor": "rgba(229, 231, 235, 1)",
            "alertColor": "orange",
            "button_face": ":material/dark_mode:",
        },
        "dark": {
            "theme.base": "light",
            "theme.backgroundColor": "#FBFBFE",
            "theme.primaryColor": "#266b97",
            "theme.secondaryBackgroundColor": "#f0f2f6",
            "theme.textColor": "#040316",
            "containerColor": "#181818",
            "containerBoundaryColor": "rgba(49, 51, 63, 0.2)",
            "alertColor": "",
            "button_face": ":material/light_mode:",
        },
    }


def change_streamlit_theme():
    previous_theme = st.session_state.themes["current_theme"]
    tdict = (
        st.session_state.themes["light"]
        if st.session_state.themes["current_theme"] == "light"
        else st.session_state.themes["dark"]
    )

    for vkey, vval in tdict.items():
        if vkey.startswith("theme"):
            st._config.set_option(vkey, vval)

    st.session_state.themes["refreshed"] = False

    if previous_theme == "dark":
        st.session_state.themes["current_theme"] = "light"

    elif previous_theme == "light":
        st.session_state.themes["current_theme"] = "dark"


if st.session_state.themes["refreshed"] == False:
    st.session_state.themes["refreshed"] = True
    st.rerun()


if __name__ == "__main__":
    # st.session_state.customer_id = "amritharaj"

    if st.session_state.customer_id:
        greeting = get_greetings(is_ist=True)
        customer_name = get_customer_details(full_name=False)

        if "customer_appliances" not in st.session_state:
            query_customer_appliances = QueryCustomerAppliances()
            st.session_state.customer_appliances = (
                query_customer_appliances.fetch_customer_appliance_data_by_customer_id(
                    customer_id=st.session_state.customer_id,
                    limit=-1,
                )
            )

        with st.sidebar:
            selected_menu_item = sac.menu(
                [
                    sac.MenuItem(
                        "My Dashboard",
                        icon="grid",
                    ),
                    sac.MenuItem(
                        "My Appliances",
                        icon="layers",
                    ),
                    sac.MenuItem(
                        "Service History",
                        icon="inboxes",
                    ),
                    sac.MenuItem(" ", disabled=True),
                    sac.MenuItem(type="divider"),
                ],
                open_all=True,
            )

            with st.container(height=323, border=False):
                with stylable_container(
                    key="sidebar_container_with_border",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                        """,
                ):
                    with st.container(border=False):
                        colx, coly = st.columns(
                            [1, 2.65], vertical_alignment="center")

                        with colx:
                            try:
                                st.image(
                                    "assets/avatars/customers/female8.png" if st.session_state.customer_details.get("gender").lower() == "female" else "assets/avatars/customers/male8.png",
                                )

                            except Exception as error:
                                st.image(
                                    "assets/avatars/customers/female8.png" if st.session_state.customer_details.get("gender").lower() == "female" else "assets/avatars/customers/male8.png",
                                )

                        with coly:
                            st.markdown(
                                f"""
                                <B>Amritha Raj</B><BR>
                                Username: {st.session_state.customer_id}
                                """,
                                unsafe_allow_html=True,
                            )

                sac.alert(
                    label=f"Trouble Viewing Content?",
                    description="Press **C** to clear cache, then **R** to refresh page.",
                    color="orange",
                    icon=True,
                )

            cola, colb = st.columns([4.5, 1])

            with cola:
                if st.button(
                    "Manage Account",
                    icon=":material/manage_accounts:",
                    use_container_width=True,
                ):
                    dialog_manage_account()

            with colb:
                if st.button(
                    "",
                    icon=":material/logout:",
                    help="Log Out",
                    use_container_width=True,
                ):
                    previous_theme = "dark"
                    tdict = st.session_state.themes["dark"]

                    for vkey, vval in tdict.items():
                        if vkey.startswith("theme"):
                            st._config.set_option(vkey, vval)

                    st.session_state.themes["refreshed"] = False
                    st.session_state.themes["current_theme"] = "light"

                    st.session_state.clear()
                    st.cache_data.clear()
                    st.cache_resource.clear()

                    st.rerun()

        if selected_menu_item == "My Dashboard":
            ribbon_col_1, ribbon_col_2, ribbon_col_3 = st.columns(
                [4.2, 1.4, 0.4], vertical_alignment="center"
            )

            with ribbon_col_1:
                st.markdown(
                    f"<H4>{greeting}, {str(st.session_state.customer_name)}! 👋</H4>",
                    unsafe_allow_html=True,
                )

            with ribbon_col_2:
                if st.button(
                    "Add New Appliance", icon=":material/add:", use_container_width=True
                ):
                    register_new_appliance()

            with ribbon_col_3:
                btn_face = (
                    st.session_state.themes["light"]["button_face"]
                    if st.session_state.themes["current_theme"] == "light"
                    else st.session_state.themes["dark"]["button_face"]
                )

                st.button(
                    "",
                    icon=btn_face,
                    use_container_width=True,
                    type="secondary",
                    on_click=change_streamlit_theme,
                )

            st.write(" ")
            col1, col2, col3, col4 = st.columns(4)

            query_customer_appliances = QueryCustomerAppliances()

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_customer_appliance_details(cache=True):
                try:
                    st.session_state.recent_appliance_serial_numbers = list(
                        st.session_state.customer_appliances.keys()
                    )

                except Exception as error:
                    pass

                    try:
                        st.session_state.recent_appliance_serial_numbers = query_customer_appliances.fetch_appliance_serial_numbers_by_customer_id(
                            customer_id=st.session_state.customer_id,
                            limit=-1,
                        )
                    except Exception as error:
                        pass

                if len(st.session_state.recent_appliance_serial_numbers) > 0:
                    try:
                        st.session_state.customer_appliance_1_details = (
                            st.session_state.customer_appliances.get(
                                st.session_state.recent_appliance_serial_numbers[0]
                            )
                        )

                    except Exception as error:
                        pass

                        try:
                            st.session_state.customer_appliance_1_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                                st.session_state.customer_id,
                                st.session_state.recent_appliance_serial_numbers[0],
                            )
                        except Exception as error:
                            pass

                if len(st.session_state.recent_appliance_serial_numbers) > 1:
                    try:
                        st.session_state.customer_appliance_2_details = (
                            st.session_state.customer_appliances.get(
                                st.session_state.recent_appliance_serial_numbers[1]
                            )
                        )

                    except Exception as error:
                        pass

                        try:
                            st.session_state.customer_appliance_2_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                                st.session_state.customer_id,
                                st.session_state.recent_appliance_serial_numbers[1],
                            )
                        except Exception as error:
                            pass

                if len(st.session_state.recent_appliance_serial_numbers) > 2:
                    try:
                        st.session_state.customer_appliance_3_details = (
                            st.session_state.customer_appliances.get(
                                st.session_state.recent_appliance_serial_numbers[2]
                            )
                        )

                    except Exception as error:
                        try:
                            st.session_state.customer_appliance_3_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                                st.session_state.customer_id,
                                st.session_state.recent_appliance_serial_numbers[2],
                            )

                        except Exception as error:
                            pass

                if len(st.session_state.recent_appliance_serial_numbers) > 3:
                    try:
                        st.session_state.customer_appliance_4_details = (
                            st.session_state.customer_appliances.get(
                                st.session_state.recent_appliance_serial_numbers[3]
                            )
                        )

                    except Exception as error:
                        try:
                            st.session_state.customer_appliance_4_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                                st.session_state.customer_id,
                                st.session_state.recent_appliance_serial_numbers[3],
                            )
                        except Exception as error:
                            pass

            fetch_and_cache_customer_appliance_details(cache=True)

            if len(st.session_state.recent_appliance_serial_numbers) > 0:
                with col1:
                    with stylable_container(
                        key="container_with_border_1",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            try:
                                st.image(
                                    st.session_state.customer_appliance_1_details[
                                        "appliance_image_url"
                                    ],
                                    use_container_width=True,
                                )
                            except Exception as error:
                                pass

                            st.markdown(
                                f"<B>{
                                    st.session_state.customer_appliance_1_details['brand']} {
                                    st.session_state.customer_appliance_1_details['category']}</B><BR>Serial No.: {
                                    st.session_state.customer_appliance_1_details['serial_number']}",
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "View Details",
                                icon=":material/notes:",
                                use_container_width=True,
                                key="_featured_appliance_1",
                            ):
                                view_customer_appliance_details(
                                    st.session_state.customer_appliance_1_details
                                )

            if len(st.session_state.recent_appliance_serial_numbers) > 1:
                with col2:
                    with stylable_container(
                        key="container_with_border_2",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            try:
                                st.image(
                                    st.session_state.customer_appliance_2_details[
                                        "appliance_image_url"
                                    ],
                                    use_container_width=True,
                                )
                            except Exception as error:
                                pass

                            st.markdown(
                                f"<B>{
                                    st.session_state.customer_appliance_2_details['brand']} {
                                    st.session_state.customer_appliance_2_details['category']}</B><BR>Serial No.: {
                                    st.session_state.customer_appliance_2_details['serial_number']}",
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "View Details",
                                icon=":material/notes:",
                                use_container_width=True,
                                key="_featured_appliance_2",
                            ):
                                view_customer_appliance_details(
                                    st.session_state.customer_appliance_2_details
                                )

            if len(st.session_state.recent_appliance_serial_numbers) > 2:
                with col3:
                    with stylable_container(
                        key="container_with_border_3",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            try:
                                st.image(
                                    st.session_state.customer_appliance_3_details[
                                        "appliance_image_url"
                                    ],
                                    use_container_width=True,
                                )
                            except Exception as error:
                                pass

                            st.markdown(
                                f"<B>{
                                    st.session_state.customer_appliance_3_details['brand']} {
                                    st.session_state.customer_appliance_3_details['category']}</B><BR>Serial No.: {
                                    st.session_state.customer_appliance_3_details['serial_number']}",
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "View Details",
                                icon=":material/notes:",
                                use_container_width=True,
                                key="_featured_appliance_3",
                            ):
                                view_customer_appliance_details(
                                    st.session_state.customer_appliance_3_details
                                )

            if len(st.session_state.recent_appliance_serial_numbers) > 3:
                with col4:
                    with stylable_container(
                        key="container_with_border_4",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            try:
                                st.image(
                                    st.session_state.customer_appliance_4_details[
                                        "appliance_image_url"
                                    ],
                                    use_container_width=True,
                                )
                            except Exception as error:
                                pass

                            st.markdown(
                                f"<B>{
                                    st.session_state.customer_appliance_4_details['brand']} {
                                    st.session_state.customer_appliance_4_details['category']}</B><BR>Serial No.: {
                                    st.session_state.customer_appliance_4_details['serial_number']}",
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "View Details",
                                icon=":material/notes:",
                                use_container_width=True,
                                key="_featured_appliance_4",
                            ):
                                view_customer_appliance_details(
                                    st.session_state.customer_appliance_4_details
                                )

            header1, header2 = st.columns([4.8, 1])

            with header1:
                st.markdown(" ", unsafe_allow_html=True)

                st.markdown(
                    """
                <H4 class="h4-recent-service-request">
                    Recent Service Requests
                </H4>
                """,
                    unsafe_allow_html=True,
                )

            with header2:
                st.markdown("<BR>", unsafe_allow_html=True)
                if st.button(
                    "Create Request",
                    icon=":material/add:",
                    use_container_width=True,
                    type="tertiary",
                ):
                    create_new_onsite_service_request()

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_customers_service_requests(cache=True):
                onsite_service_request_collection = OnsiteServiceRequestCollection()

                st.session_state.customers_service_requests_list = onsite_service_request_collection.fetch_latest_service_request_by_customer_id(
                    customer_id=st.session_state.customer_id,
                    limit=-1,
                )

            fetch_and_cache_customers_service_requests(cache=True)

            for i in range(
                    len(st.session_state.customers_service_requests_list)):
                if i >= 2:
                    break
                service_request_id, service_request_details = (
                    st.session_state.customers_service_requests_list[i]
                )

                with stylable_container(
                    key=f"container_with_border_{i}",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                    """,
                ):
                    cola, colb, colc = st.columns([0.84, 2.72, 1.5])

                    with cola:
                        st.image(
                            service_request_details["appliance_details"][
                                "appliance_image_url"
                            ],
                            use_container_width=True,
                        )

                    with colb:
                        colx, coly = st.columns([20, 0.01])
                        with colx:
                            st.markdown(
                                f"<H5>{
                                    service_request_details['request_title']}</H5>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"""
                                {service_request_details['appliance_details']['sub_category']}
                                &nbsp;•&nbsp; {service_request_id}
                                """,
                                unsafe_allow_html=True,
                            )

                            st.markdown(
                                f"""
                                <div class="div-truncate-text">
                                    <P align='left'>
                                        {service_request_details['description']}...
                                    </P>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with colc:
                        st.markdown("<BR>", unsafe_allow_html=True)

                        st.markdown(
                            f"""
                            <P class="p-rsr-1" align='right'>
                                <font size=4>
                                    <B>
                                        Status:
                                        {service_request_details['ticket_status'].capitalize()}
                                        &nbsp;
                                    </B>
                                </font>
                            </P>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.write(" ")
                        colx, coly = st.columns([0.9, 3])

                        with colx:
                            if st.button(
                                "",
                                icon=":material/edit:",
                                use_container_width=True,
                                help="Edit",
                                key=f"_recent_service_request_b1{i}",
                            ):
                                edit_service_request_details(
                                    service_request_id, service_request_details
                                )

                        with coly:
                            if st.button(
                                "View Details",
                                icon=":material/page_info:",
                                use_container_width=True,
                                key=f"_recent_service_request_details_{i}",
                            ):
                                view_service_request_details(
                                    service_request_id, service_request_details
                                )

            header1, header2 = st.columns([5.75, 1])

            with header1:
                st.markdown(" ", unsafe_allow_html=True)

                st.markdown(
                    """
                <H4 class="h4-recent-service-request">
                    Repair Guides & Tutorials
                </H4>
                """,
                    unsafe_allow_html=True,
                )

            with header2:
                st.markdown("<BR>", unsafe_allow_html=True)
                st.link_button(
                    "View Library",
                    url="https://www.youtube.com/@bensappliancesandjunk",
                    icon=":material/video_library:",
                    use_container_width=True,
                    type="tertiary",
                )

            col1, col2, col3 = st.columns(3)

            with col1:
                with stylable_container(
                    key="video_container_with_border_1",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                    """,
                ):
                    with st.container(border=False):
                        video_url_1 = "https://youtu.be/Hn2pXXF0PEg?si=s4rCspSXkWyfHK5Z"

                        st.video(video_url_1)
                        st.markdown(
                            """
                            <B>Amana Washer Repair Guide</B><BR>YouTube Tutorial by Appliance Video""",
                            unsafe_allow_html=True,
                        )

                        st.link_button(
                            "Watch on Youtube",
                            url=video_url_1,
                            use_container_width=True,
                            icon=":material/smart_display:",
                        )

            with col2:
                with stylable_container(
                    key="video_container_with_border_2",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                    """,
                ):
                    with st.container(border=False):
                        video_url_2 = "https://youtu.be/tENq5YFegwg?si=TPAhRBgw-paSceEP"

                        st.video(video_url_2)
                        st.markdown(
                            "<B>Amana Refrigerator Guide</B><BR>YouTube Tutorial by Appliance Video",
                            unsafe_allow_html=True,
                        )

                        st.link_button(
                            "Watch on Youtube",
                            url=video_url_2,
                            use_container_width=True,
                            icon=":material/smart_display:",
                        )

            with col3:
                with stylable_container(
                    key="video_container_with_border_3",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                    """,
                ):
                    with st.container(border=False):
                        video_url_3 = "https://youtu.be/r6QzCgpFpP4?si=g-oHEy9ZMAQdVqSM"

                        st.video(video_url_3)
                        st.markdown(
                            "<B>Amana Refrigerator Troubleshoot</B><BR>YouTube Tutorial by Appliance Video",
                            unsafe_allow_html=True,
                        )

                        st.link_button(
                            "Watch on Youtube",
                            url=video_url_3,
                            use_container_width=True,
                            icon=":material/smart_display:",
                        )

            header1, header2 = st.columns([5.75, 1])

            with header1:
                st.markdown(" ", unsafe_allow_html=True)
                st.markdown(
                    """
                <H4 class="h4-recent-service-request">
                    Latest in the Marketplace
                </H4>
                """,
                    unsafe_allow_html=True,
                )

            with header2:
                st.markdown("<BR>", unsafe_allow_html=True)
                if st.button(
                    "Explore More",
                    icon=":material/store:",
                    use_container_width=True,
                    type="tertiary",
                    key="_explore_marketplace",
                ):
                    st.toast("Marketplace is currently unavailable")

            col1, col2, col3, col4 = st.columns(4)

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_best_appliances_by_energy_rating(cache=True):
                query_appliances = Appliances()

                st.session_state.best_appliancs_by_energy_rating = (
                    query_appliances.fetch_best_appliances_by_energy_rating(
                        count=4)
                )

            fetch_and_cache_best_appliances_by_energy_rating(cache=True)

            if st.session_state.best_appliancs_by_energy_rating:
                appliance_1, appliance_2, appliance_3, appliance_4 = (
                    st.session_state.best_appliancs_by_energy_rating
                )

                with col1:
                    with stylable_container(
                        key="featured_container_with_border_1",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                        """,
                    ):
                        with st.container(border=False):
                            st.image(appliance_2[3], use_container_width=True)

                            appliance_name = (
                                appliance_2[2]
                                + " "
                                + appliance_2[0].replace("Countertop ", "")
                            )

                            st.markdown(
                                f"""
                                <P><B>{appliance_name}</B><BR>
                                Model No.: {appliance_2[1]}</P>
                                """,
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "Visit Marketplace",
                                use_container_width=True,
                                icon=":material/store:",
                                key="_buy_appliance_2",
                            ):
                                st.toast(
                                    "Marketplace is currently unavailable")

                with col2:
                    with stylable_container(
                        key="featured_container_with_border_2",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                        """,
                    ):
                        with st.container(border=False):
                            st.image(appliance_1[3], use_container_width=True)

                            appliance_name = (
                                appliance_1[2]
                                + " "
                                + appliance_1[0].replace("Countertop ", "")
                            )

                            st.markdown(
                                f"""
                                <P><B>{appliance_name}</B><BR>
                                Model No.: {appliance_1[1]}</P>
                                """,
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "Visit Marketplace",
                                use_container_width=True,
                                icon=":material/store:",
                                key="_buy_appliance_1",
                            ):
                                st.toast(
                                    "Marketplace is currently unavailable")

                with col3:
                    with stylable_container(
                        key="featured_container_with_border_3",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                        """,
                    ):
                        with st.container(border=False):
                            st.image(appliance_3[3], use_container_width=True)

                            appliance_name = (
                                appliance_3[2]
                                + " "
                                + appliance_3[0].replace("Countertop ", "")
                            )

                            st.markdown(
                                f"""
                                <P><B>{appliance_name}</B><BR>
                                Model No.: {appliance_3[1]}</P>
                                """,
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "Visit Marketplace",
                                use_container_width=True,
                                icon=":material/store:",
                                key="_buy_appliance_3",
                            ):
                                st.toast(
                                    "Marketplace is currently unavailable")

                with col4:
                    with stylable_container(
                        key="featured_container_with_border_4",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                        """,
                    ):
                        with st.container(border=False):
                            st.image(appliance_4[3], use_container_width=True)

                            appliance_name = (
                                appliance_4[2]
                                + " "
                                + appliance_4[0].replace("Countertop ", "")
                            )

                            st.markdown(
                                f"""
                                <P><B>{appliance_name}</B><BR>
                                Model No.: {appliance_4[1]}</P>
                                """,
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "Visit Marketplace",
                                use_container_width=True,
                                icon=":material/store:",
                                key="_buy_appliance_4",
                            ):
                                st.toast(
                                    "Marketplace is currently unavailable")

        elif selected_menu_item == "My Appliances":
            ribbon_col_1, ribbon_col_2, ribbon_col_3 = st.columns(
                [4.2, 1.4, 0.4], vertical_alignment="center"
            )

            with ribbon_col_1:
                st.markdown(
                    f"<H4>{greeting}, {str(st.session_state.customer_name)}! 👋</H4>",
                    unsafe_allow_html=True,
                )

            with ribbon_col_2:
                if st.button(
                    "Add New Appliance", icon=":material/add:", use_container_width=True
                ):
                    create_new_onsite_service_request()

            with ribbon_col_3:
                btn_face = (
                    st.session_state.themes["light"]["button_face"]
                    if st.session_state.themes["current_theme"] == "light"
                    else st.session_state.themes["dark"]["button_face"]
                )

                st.button(
                    "",
                    icon=btn_face,
                    use_container_width=True,
                    type="secondary",
                    on_click=change_streamlit_theme,
                )

            st.write(" ")
            col1, col2, col3, col4 = st.columns(4)

            # st.session_state.customer_appliances

            for idx, appliance_serial_number in enumerate(
                list(st.session_state.customer_appliances.keys())
            ):
                query_customer_appliances = QueryCustomerAppliances()

                try:
                    appliance_details = st.session_state.customer_appliances.get(
                        appliance_serial_number
                    )

                except Exception as error:
                    appliance_details = query_customer_appliances.fetch_customer_appliance_details_by_customer_id_serial_number(
                        st.session_state.customer_id,
                        appliance_serial_number,
                    )

                if idx % 4 == 0:
                    with col1:
                        with stylable_container(
                            key="appliance_container_with_border_1",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                            """,
                        ):
                            with st.container(border=False):
                                st.image(
                                    appliance_details["appliance_image_url"],
                                    use_container_width=True,
                                )
                                st.markdown(
                                    f"<B>{
                                        appliance_details['brand']} {
                                        appliance_details['category']}</B><BR>Serial No.: {
                                        appliance_details['serial_number']}",
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "View Details",
                                    icon=":material/notes:",
                                    use_container_width=True,
                                    key=f"_featured_appliance_{idx}",
                                ):
                                    view_customer_appliance_details(
                                        appliance_details)

                        st.write(" ")

                elif idx % 4 == 1:
                    with col2:
                        with stylable_container(
                            key="appliance_container_with_border_2",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                            """,
                        ):
                            with st.container(border=False):
                                st.image(
                                    appliance_details["appliance_image_url"],
                                    use_container_width=True,
                                )
                                st.markdown(
                                    f"<B>{
                                        appliance_details['brand']} {
                                        appliance_details['category']}</B><BR>Serial No.: {
                                        appliance_details['serial_number']}",
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "View Details",
                                    icon=":material/notes:",
                                    use_container_width=True,
                                    key=f"_featured_appliance_{idx}",
                                ):
                                    view_customer_appliance_details(
                                        appliance_details)

                        st.write(" ")

                elif idx % 4 == 2:
                    with col3:
                        with stylable_container(
                            key="appliance_container_with_border_3",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                            """,
                        ):
                            with st.container(border=False):
                                st.image(
                                    appliance_details["appliance_image_url"],
                                    use_container_width=True,
                                )
                                st.markdown(
                                    f"<B>{
                                        appliance_details['brand']} {
                                        appliance_details['category']}</B><BR>Serial No.: {
                                        appliance_details['serial_number']}",
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "View Details",
                                    icon=":material/notes:",
                                    use_container_width=True,
                                    key=f"_featured_appliance_{idx}",
                                ):
                                    view_customer_appliance_details(
                                        appliance_details)

                        st.write(" ")

                elif idx % 4 == 3:
                    with col4:
                        with stylable_container(
                            key="appliance_container_with_border_4",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                            """,
                        ):
                            with st.container(border=False):
                                st.image(
                                    appliance_details["appliance_image_url"],
                                    use_container_width=True,
                                )
                                st.markdown(
                                    f"<B>{
                                        appliance_details['brand']} {
                                        appliance_details['category']}</B><BR>Serial No.: {
                                        appliance_details['serial_number']}",
                                    unsafe_allow_html=True,
                                )

                                if st.button(
                                    "View Details",
                                    icon=":material/notes:",
                                    use_container_width=True,
                                    key=f"_featured_appliance_{idx}",
                                ):
                                    view_customer_appliance_details(
                                        appliance_details)

                        st.write(" ")
            st.write(" ")

        elif selected_menu_item == "Service History":
            ribbon_col_1, ribbon_col_2, ribbon_col_3 = st.columns(
                [4.2, 1.4, 0.4], vertical_alignment="center"
            )

            with ribbon_col_1:
                st.markdown(
                    f"<H4>{greeting}, {str(st.session_state.customer_name)}! 👋</H4>",
                    unsafe_allow_html=True,
                )

            with ribbon_col_2:
                if st.button(
                    "Create New Request",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    create_new_onsite_service_request()

            with ribbon_col_3:
                btn_face = (
                    st.session_state.themes["light"]["button_face"]
                    if st.session_state.themes["current_theme"] == "light"
                    else st.session_state.themes["dark"]["button_face"]
                )

                st.button(
                    "",
                    icon=btn_face,
                    use_container_width=True,
                    type="secondary",
                    on_click=change_streamlit_theme,
                )

            st.write(" ")

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_all_customer_service_requests(cache=True):
                onsite_service_request_collection = OnsiteServiceRequestCollection()

                st.session_state.all_customers_service_requests_list = onsite_service_request_collection.fetch_all_service_request_by_customer_id(
                    customer_id=st.session_state.customer_id,
                )

            fetch_and_cache_all_customer_service_requests(cache=True)

            for i in range(
                    len(st.session_state.customers_service_requests_list)):
                service_request_id, service_request_details = (
                    st.session_state.customers_service_requests_list[i]
                )

                with stylable_container(
                    key=f"all_service_requests_container_with_border_{i}",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                    """,
                ):
                    cola, colb, colc = st.columns([0.84, 2.72, 1.5])

                    with cola:
                        st.image(
                            service_request_details["appliance_details"][
                                "appliance_image_url"
                            ],
                            use_container_width=True,
                        )

                    with colb:
                        colx, coly = st.columns([20, 0.01])
                        with colx:
                            st.markdown(
                                f"<H5>{
                                    service_request_details['request_title']}</H5>",
                                unsafe_allow_html=True,
                            )
                            st.write(
                                f"{
                                    service_request_details['appliance_details']['sub_category']} • {service_request_id}"
                            )
                            st.markdown(
                                f"""
                                <div class="div-truncate-text">
                                    <P align='left'>
                                        {service_request_details['description']}...
                                    </P>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with colc:
                        st.markdown("<BR>", unsafe_allow_html=True)
                        st.markdown(
                            f"""<P class="p-rsr-1" align='right'><font size=4><B>Status: {
                                service_request_details['ticket_status'].capitalize()}&nbsp</B></font></P>""",
                            unsafe_allow_html=True,
                        )
                        st.write(" ")

                        colx, coly = st.columns([1, 3])
                        with colx:
                            if st.button(
                                "",
                                icon=":material/edit:",
                                help="Edit",
                                use_container_width=True,
                                key=f"_edit_service_request_{i}",
                            ):
                                edit_service_request_details(
                                    service_request_id, service_request_details
                                )

                        with coly:
                            if st.button(
                                "View Details",
                                icon=":material/page_info:",
                                use_container_width=True,
                                key=f"_recent_service_request_details_{i}",
                            ):
                                view_service_request_details(
                                    service_request_id, service_request_details
                                )

            st.write(" ")

    else:
        if "themes" not in st.session_state:
            st.session_state.themes = {
                "current_theme": "light",
                "refreshed": True,
                "light": {
                    "theme.base": "dark",
                    "theme.backgroundColor": "#111111",
                    "theme.primaryColor": "#64ABD8",
                    "theme.secondaryBackgroundColor": "#181818",
                    "theme.textColor": "#EAE9FC",
                    "containerColor": "#f0f2f6",
                    "containerBoundaryColor": "rgba(229, 231, 235, 1)",
                    "alertColor": "orange",
                    "button_face": ":material/dark_mode:",
                },
                "dark": {
                    "theme.base": "light",
                    "theme.backgroundColor": "#FBFBFE",
                    "theme.primaryColor": "#266b97",
                    "theme.secondaryBackgroundColor": "#f0f2f6",
                    "theme.textColor": "#040316",
                    "containerColor": "#181818",
                    "containerBoundaryColor": "rgba(49, 51, 63, 0.2)",
                    "alertColor": "",
                    "button_face": ":material/light_mode:",
                },
            }

        try:
            firebase_credentials = credentials.Certificate(
                "config/firebase_service_account_key.json"
            )
            firebase_admin.initialize_app(firebase_credentials)

        except Exception as error:
            pass

        col_login_forum, col_image = st.columns(2)

        with col_image:
            st.write(" ")

            if st.session_state.themes["current_theme"] == "dark":
                st.image("assets/app_graphics/welcome_banner_dark.png")

            else:
                st.image("assets/app_graphics/welcome_banner_light.png")

        with col_login_forum:
            colx, _ = st.columns([1.15, 3.85])
            colx.markdown("<BR>", unsafe_allow_html=True)

            if st.session_state.themes["current_theme"] == "dark":
                colx.image(
                    "assets/logos/logiq_logo_dark.png",
                    use_container_width=True)

            else:
                colx.image(
                    "assets/logos/logiq_logo_light.png", use_container_width=True
                )

            st.markdown("<BR>" * 2, unsafe_allow_html=True)
            st.markdown(
                "<H2>Welcome to LogIQ!</H2>LogIn to access the customer app. New here? Create an account to get started!",
                unsafe_allow_html=True,
            )

            st.write(" ")
            colx, _ = st.columns([8, 1])

            email = bleach.clean(
                colx.text_input(
                    "Username",
                    placeholder="Enter your username",
                    label_visibility="collapsed",
                )
            )

            password = bleach.clean(
                colx.text_input(
                    "Password",
                    placeholder="Enter your password",
                    type="password",
                    label_visibility="collapsed",
                )
            )

            col1, col2, _ = st.columns([1.5, 1, 0.1], vertical_alignment="top")
            checkbox_remember_me = col1.checkbox("Remember me", value=True)

            if col2.button(
                label="Forgot Password?", use_container_width=True, type="tertiary"
            ):
                reset_password()

            cola, colb, _ = st.columns([7.1, 0.9, 1])

            button_login = cola.button(
                "LogIn to the Customer App", use_container_width=True, type="primary"
            )

            if colb.button(
                "",
                icon=":material/copyright:",
                help="Attribution",
                use_container_width=True,
            ):
                dialog_attribution()

            if st.session_state.customer_id is False:
                colx, _ = st.columns([8, 1])

                warning_message = colx.error(
                    "Invalid Username or Password", icon=":material/error:"
                )

                time.sleep(3)
                st.session_state.customer_id = None

                warning_message.empty()

            if button_login:
                email = email.lower()

                try:
                    api_key = st.secrets["FIREBASE_AUTH_WEB_API_KEY"]
                    base_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

                    if "@" not in email:
                        username = email.lower()
                        user = firebase_admin.auth.get_user(username)
                        email = user.email

                    query_customers = QueryCustomers()
                    customer_exists = query_customers.check_customer_exists_by_email(
                        email
                    )

                    if customer_exists:
                        data = {"email": email, "password": password}

                        response = requests.post(
                            base_url.format(api_key=api_key), json=data
                        )

                        if response.status_code == 200:
                            st.toast("Logging you in to the customer app")
                            data = response.json()
                                                        
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            
                            st.session_state.customer_id = (
                                firebase_admin.auth.get_user_by_email(
                                    email).uid
                            )
                            st.rerun()

                        else:
                            st.session_state.customer_id = False
                            st.rerun()

                    else:
                        st.toast(
                            "No customer found with this username. Please check the username and try again."
                        )

                        st.session_state.customer_id = False
                        time.sleep(5)

                        st.rerun()

                except Exception as error:
                    st.session_state.customer_id = False
                    st.rerun()
