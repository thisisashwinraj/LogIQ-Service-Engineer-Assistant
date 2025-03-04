import time
import json
import base64
import numpy as np
import pandas as pd

import bleach
import requests
from PIL import Image
from google.genai import types

import dateutil
import datetime
from datetime import timedelta

import streamlit as st
import streamlit_antd_components as sac
from streamlit_folium import folium_static, st_folium
from streamlit_extras.stylable_container import stylable_container

import firebase_admin
from firebase_admin import auth, credentials

from backend.utils.geo_operations import LocationServices
from backend.channels.email_client import TransactionalEmails
from backend.channels.sms_client import NotificationSMS

from database.firebase.firestore import OnsiteServiceRequestCollection
from database.cloud_sql.queries import Appliances, QueryCustomers, QueryEngineers
from database.cloud_sql.migrations import MigrateEngineers
from database.cloud_storage.document_storage import (
    CustomerRecordsBucket,
    ServiceManualBucket,
)
from database.cloud_storage.multimedia_storage import ProfilePicturesBucket

from inference.chatbot import ServiceEngineerChatbot


st.set_page_config(
    page_title="LogIQ: Engineer App",
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

with open("assets/css/engineers.css") as f:
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


if "engineer_id" not in st.session_state:
    st.session_state.engineer_id = None

if "engineer_details" not in st.session_state:
    st.session_state.engineer_details = None

if "onsite_service_requests" not in st.session_state:
    st.session_state.onsite_service_requests = []

if "cache_model_number" not in st.session_state:
    st.session_state.cache_model_number = None

if "flag_use_context_cache" not in st.session_state:
    st.session_state.flag_use_context_cache = None

if "service_guide" not in st.session_state:
    st.session_state.service_guide = None

if "ticket_counts" not in st.session_state:
    st.session_state.ticket_counts = {}

if "distinct_appliance_details" not in st.session_state:
    try:
        query_appliances = Appliances()
        st.session_state.distinct_appliance_details = (
            query_appliances.fetch_distinct_appliance_data()
        )
    except Exception as error:
        pass


def set_cache_model_number(brand, sub_category, model_number):
    st.session_state.cache_model_number = model_number
    st.session_state.cache_brand = brand
    st.session_state.cache_sub_category = sub_category


@st.cache_data(ttl="60 minutes", show_spinner=False)
def build_context_cache(
    input_brand, input_category, input_sub_category, input_model_number
):
    service_manual_uri = (
        "gs://service_manual_bucket/"
        + input_category.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        + "/"
        + input_sub_category.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        + "_service_guide.pdf"
    )

    # files_to_upload = [service_manual_uri, service_manual_uri, service_manual_uri]
    files_to_upload = [service_manual_uri]

    service_guide_title = (
        input_brand + " " + input_sub_category + " " + input_model_number
    )

    service_engineer_chatbot = ServiceEngineerChatbot()
    context_cache = service_engineer_chatbot.construct_cache_model(
        input_brand,
        input_sub_category,
        input_model_number,
        service_guide_title,
        files_to_upload,
    )

    return context_cache


@st.dialog("Manage Account", width="large")
def dialog_manage_account():
    cola, _, colb, colc = st.columns(
        [1, 0.05, 2.9, 1.1], vertical_alignment="top")

    with cola:
        st.image(
            "assets/avatars/customers/male3.png",
            use_container_width=True,
        )

    with colb:
        st.write(" ")
        st.markdown(
            f"""
            <H2 class="h2-vsrd-3">
                {st.session_state.engineer_details.get('first_name')} {st.session_state.engineer_details.get('last_name')}
            </H2>
            Engineer Id: {st.session_state.engineer_id}
            &nbsp;• &nbsp;Ratings: {str(float(st.session_state.engineer_details.get('rating')))} ⭐
            """,
            unsafe_allow_html=True,
        )

        st.write(" ")
        st.markdown(
            f"""
            Open: {str(st.session_state.ticket_counts.get('assigned')).zfill(2) if st.session_state.ticket_counts.get('assigned') < 10 else str(st.session_state.ticket_counts.get('assigned'))}
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            Resolved: {str(st.session_state.ticket_counts.get('resolved')).zfill(2) if st.session_state.ticket_counts.get('resolved') < 10 else str(st.session_state.ticket_counts.get('resolved'))}
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            Pending Confirmation: {str(st.session_state.ticket_counts.get('pending')).zfill(2) if st.session_state.ticket_counts.get('pending') < 10 else str(st.session_state.ticket_counts.get('pending'))}
            """,
            unsafe_allow_html=True,
        )

    with colc:
        st.markdown("<BR>", unsafe_allow_html=True)
        button_engineer_availability = st.button(
            (
                "Available"
                if st.session_state.engineer_details.get("availability") == 1
                else "Unavailable"
            ),
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.engineer_details.get("availability") == 1
                else "secondary"
            ),
            icon=(
                ":material/person_check:"
                if st.session_state.engineer_details.get("availability") == 1
                else ":material/person_alert:"
            ),
        )

    if button_engineer_availability:
        with st.spinner("Updating availability status...", show_time=True):
            migrate_engineers = MigrateEngineers()
            response = migrate_engineers.toggle_engineer_availability(
                st.session_state.engineer_id
            )

            st.session_state.engineer_details = None

        if response:
            st.success(
                "Availability status updated succesfully!", icon=":material/check:"
            )

            try:
                query_engineers = QueryEngineers()
                st.session_state.engineer_details = (
                    query_engineers.fetch_engineer_details_by_id(
                        st.session_state.engineer_id
                    )
                )

            except Exception as error:
                pass

        else:
            alert_warning = st.warning(
                "Unable to update your availability status. Please try again later.",
                icon=":material/warning:",
            )
            time.sleep(3)

        st.rerun()

    st.write(" ")
    selected_tab = sac.tabs(
        [
            sac.TabsItem(label="Personal Details"),
            sac.TabsItem(label="Skills and Specializations"),
            sac.TabsItem(label="Location Details"),
        ],
        variant="outline",
    )

    if selected_tab == "Personal Details":
        cola, colb = st.columns(2)
        first_name = bleach.clean(
            cola.text_input(
                "First Name", value=st.session_state.engineer_details.get("first_name")
            )
        )
        last_name = bleach.clean(
            colb.text_input(
                "Last Name", value=st.session_state.engineer_details.get("last_name")
            )
        )

        phone_number = bleach.clean(
            cola.text_input(
                "Phone Number",
                value=st.session_state.engineer_details.get("phone_number"),
            )
        )
        email = bleach.clean(
            colb.text_input(
                "Email Id", value=st.session_state.engineer_details.get("email")
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
            migrate_engineers = MigrateEngineers()
            profile_picture_url = None

            with st.spinner("Updating details...", show_time=True):
                if profile_picture:
                    try:
                        profile_pictures_bucket = ProfilePicturesBucket()

                        profile_picture_url = (
                            profile_pictures_bucket.upload_profile_picture(
                                user_type="engineers",
                                user_id=st.session_state.engineer_id,
                                file=profile_picture,
                            )
                        )

                    except Exception as error:
                        st.warning(
                            "Unable to save profile picture", icon=":material/warning:"
                        )

                    finally:
                        if profile_picture_url:
                            response = migrate_engineers.update_engineer(
                                engineer_id=st.session_state.engineer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                                profile_picture=profile_picture_url,
                            )

                        else:
                            response = migrate_engineers.update_engineer(
                                engineer_id=st.session_state.engineer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                            )

                else:
                    response = migrate_engineers.update_engineer(
                        engineer_id=st.session_state.engineer_id,
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
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                try:
                    get_engineer_name.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
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

    elif selected_tab == "Skills and Specializations":
        specializations_options = list(
            st.session_state.distinct_appliance_details.keys()
        )
        specializations = st.multiselect(
            "Specializations",
            specializations_options,
            default=json.loads(
                st.session_state.engineer_details.get("specializations", None)
            ),
        )

        skills_options = [
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
        skills = st.multiselect(
            "Skills",
            skills_options,
            default=json.loads(
                st.session_state.engineer_details.get(
                    "skills", None)),
        )

        language_options = ["English", "Hindi", "Malayalam", "Tamil"]
        language_proficiency = st.multiselect(
            "Language Proficiency",
            language_options,
            default=json.loads(
                st.session_state.engineer_details.get(
                    "language_proficiency", None)
            ),
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            use_container_width=True,
        ):
            migrate_engineers = MigrateEngineers()

            with st.spinner("Updating details...", show_time=True):
                response = migrate_engineers.update_engineer(
                    engineer_id=st.session_state.engineer_id,
                    skills=json.dumps(skills),
                    specializations=json.dumps(specializations),
                    language_proficiency=json.dumps(language_proficiency),
                )

            if response:
                st.success(
                    "Profile updated succesfully!",
                    icon=":material/check:")

                try:
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
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
        cola, colb = st.columns([3, 1])

        street = bleach.clean(
            cola.text_input(
                "Street", value=st.session_state.engineer_details.get("street")
            )
        )

        city = bleach.clean(
            colb.text_input(
                "City", value=st.session_state.engineer_details.get("city"))
        )

        cola, colb, colc, cold = st.columns(4)

        district = bleach.clean(
            cola.text_input(
                "District", value=st.session_state.engineer_details.get("district")
            )
        )

        state = bleach.clean(
            colb.text_input(
                "State", value=st.session_state.engineer_details.get("state")
            )
        )

        zip_code = bleach.clean(
            colc.text_input(
                "Zip Code", value=st.session_state.engineer_details.get("zip_code")
            )
        )

        country = bleach.clean(
            cold.text_input(
                "Country", value=st.session_state.engineer_details.get("country")
            )
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            use_container_width=True,
        ):
            migrate_engineers = MigrateEngineers()

            with st.spinner("Updating details...", show_time=True):
                response = migrate_engineers.update_engineer(
                    engineer_id=st.session_state.engineer_id,
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
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
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
                query_engineers = QueryEngineers()
                engineer_exists = query_engineers.check_engineer_exists_by_email(
                    input_email)

            except Exception as error:
                engineer_exists = None

        if engineer_exists:
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
                "No engineer found with this username. Please check the username and try again.",
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


@st.dialog("Resolve Service Request", width="large")
def dialog_resolve_service_request(
        service_request_id, service_request_details):
    if service_request_details.get("resolution").get("start_date") == "":
        sac.alert(
            label=f"Request verification OTP from the customer",
            description="Enter the OTP in the verification field to proceed with the resolution. If you are unable to obtain the OTP, please contact our Support Team at customersupport@logiq.com for further assistance.",
            color="orange",
            icon=True,
        )

    else:
        action_performed = bleach.clean(
            st.text_area(
                "Action Performed",
                placeholder="Describe the actions taken to resolve the issue in detail...",
            )
        )

        additional_notes = bleach.clean(
            st.text_area(
                "Additional Notes",
                placeholder="Add any extra details, observations, or suggestions related to the issue...",
            )
        )

        cola, colb = st.columns(2)

        with cola:
            resolution_otp = bleach.clean(
                st.text_input(
                    "Resolution OTP",
                    placeholder="Enter Customer OTP to resolve ticket",
                )
            )

        with colb:
            st.date_input("Resolution Date", disabled=True)

        cola, _ = st.columns([1, 2.5])

        if cola.button(
            "Mark as Resolved", icon=":material/done_all:", use_container_width=True
        ):
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            response, response_code = (
                onsite_service_request_collection.resolve_service_request(
                    service_request_details.get("customer_id"),
                    service_request_id,
                    action_performed,
                    additional_notes,
                    resolution_otp,
                )
            )

            if response:
                st.success(
                    "Service request has been marked as resolved!",
                    icon=":material/check:",
                )

                try:
                    try:
                        query_customers = QueryCustomers()

                        customer_name = (
                            query_customers.fetch_customer_details_by_username(
                                service_request_details.get("customer_id"),
                                ["first_name", "last_name"],
                            )
                        )

                    except Exception as error:
                        customer_name = {
                            "first_name": "LogIQ",
                            "last_name": "User",
                        }

                    transaction_email_channel = TransactionalEmails()

                    transaction_email_channel.send_onsite_service_request_resolved_mail(
                        receiver_full_name=f"{
                            customer_name.get('first_name')} {
                            customer_name.get('last_name')}",
                        receiver_email=service_request_details.get(
                            "customer_contact"
                        ).get("email"),
                        service_request_id=service_request_id,
                        engineer_id=st.session_state.engineer_id,
                        engineer_name=f"{
                            st.session_state.engineer_details.get("first_name")} {
                            st.session_state.engineer_details.get("last_name")}",
                        ticket_activity=action_performed,
                        additional_notes=additional_notes,
                    )

                except Exception as error:
                    pass

                try:
                    notification_sms_channel = NotificationSMS()

                    notification_sms_channel.send_onsite_service_request_resolved_sms(
                        receivers_phone_number=service_request_details.get(
                            "customer_contact"
                        ).get("phone_number"),
                        service_request_id=service_request_id,
                        engineer_name=f"{
                            st.session_state.engineer_details.get("first_name")} {
                            st.session_state.engineer_details.get("last_name")}",
                    )

                except Exception as error:
                    pass

                del st.session_state.onsite_service_requests
                st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                    st.session_state.engineer_id
                )

                time.sleep(3)
                st.rerun()

            else:
                if response_code == 401:
                    display_warning = st.warning(
                        "You've provided an invalid OTP. Kindly try again!",
                        icon=":material/warning:",
                    )

                elif response_code == 402:
                    display_warning = st.warning(
                        "OTP not found. Kindly request customer to generate a new OTP",
                        icon=":material/warning:",
                    )

                else:
                    display_warning = st.warning(
                        "Unable to reach server. Kindly try again later!",
                        icon=":material/warning:",
                    )

                time.sleep(3)
                display_warning.empty()


@st.dialog("Resolution Details", width="large")
def dialog_display_resolution_details(service_request_details):
    cola, colb = st.columns([0.1, 0.15], vertical_alignment="center")

    with colb:
        request_raised_on = datetime.datetime.strptime(
            service_request_details.get("created_on"),
            "%Y-%m-%d %H:%M:%S",
        ).strftime("%B %d, %Y")

        st.markdown(
            f"""
            <P align='right'>
                <B>Raised on:</B> {request_raised_on}
            </P>
            """,
            unsafe_allow_html=True,
        )

    with cola:
        st.markdown(
            "<H3>Service Request Description</H3>",
            unsafe_allow_html=True)

    st.markdown(
        f"""
        <P>
            <B>Request Title:</B>
            {service_request_details.get('request_title')}
        </P>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <P align='left'>
            <B>Description:</B>
            {service_request_details.get('description')}
        </P>
        """,
        unsafe_allow_html=True,
    )

    sac.divider(align="center", color="#181818")
    cola, colb = st.columns([0.1, 0.15], vertical_alignment="center")

    with cola:
        st.markdown(
            "<H3>Engineer Activity and Resolution</H3>",
            unsafe_allow_html=True)

        resolution_start_date = datetime.datetime.strptime(
            service_request_details.get("resolution").get("start_date"),
            "%Y-%m-%d %H:%M:%S",
        ).strftime("%B %d, %Y")

        resolution_end_date = datetime.datetime.strptime(
            service_request_details.get("resolution").get("end_date"),
            "%Y-%m-%d %H:%M:%S",
        ).strftime("%B %d, %Y")

    with colb:
        st.markdown(
            f"""
            <P align='right'>
                {resolution_start_date} - {resolution_end_date}
            </P>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <P align='left'>
            {service_request_details.get('resolution').get('action_performed', '')}
        </P>
        <P align='left'>
            {service_request_details.get('resolution').get('additional_notes', '')}
        </P>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Review Service Request", width="small")
def dialog_review_service_request(service_request_id, service_request_details):
    sac.alert(
        label=f"Do you want to assign this ticket to yourself?",
        description="Approving this request'll add it to your work queue. Note: Once selected, this action can not be undone!",
        color="orange",
        icon=True,
    )

    onsite_service_request_collection = OnsiteServiceRequestCollection()
    cola, colb = st.columns(2)

    if cola.button(
        "Approve Request",
        icon=":material/check:",
        use_container_width=True,
        type="primary",
    ):
        status_updated = onsite_service_request_collection.update_assignment_status(
            service_request_details.get("customer_id"),
            service_request_id,
            "confirmed",
        )

        try:
            query_customers = QueryCustomers()

            customer_name = query_customers.fetch_customer_details_by_username(
                service_request_details.get("customer_id"), [
                    "first_name", "last_name"]
            )

        except Exception as error:
            customer_name = {
                "first_name": "LogIQ",
                "last_name": "User",
            }

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            onsite_service_request_collection.add_service_request_activity(
                service_request_details.get("customer_id"),
                service_request_id,
                added_by="system",
                notes=f"Onsite service request assigned to {
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")} (Engineer Id: {
                    st.session_state.engineer_id})",
            )

        except Exception as error:
            pass

        try:
            transaction_email_channel = TransactionalEmails()

            transaction_email_channel.send_onsite_service_request_engineer_assigned_mail(
                receiver_full_name=f"{
                    customer_name.get('first_name')} {
                    customer_name.get('last_name')}",
                receiver_email=service_request_details.get("customer_contact").get(
                    "email"
                ),
                service_request_id=service_request_id,
                engineer_id=st.session_state.engineer_id,
                engineer_name=f"{
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")}",
                engineer_phone=st.session_state.engineer_details.get(
                    "phone_number"),
                engineer_email=st.session_state.engineer_details.get("email"),
            )

        except Exception as error:
            pass

        try:
            notification_sms_channel = NotificationSMS()

            notification_sms_channel.send_onsite_service_request_engineer_assigned_sms(
                receivers_phone_number=service_request_details.get(
                    "customer_contact"
                ).get("phone_number"),
                service_request_id=service_request_id,
                engineer_id=st.session_state.engineer_id,
                engineer_name=f"{
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")}",
            )

        except Exception as error:
            pass

        if status_updated:
            st.success(
                "Request assigned to you successfully",
                icon=":material/check:")

        else:
            st.warning(
                "Unable to update staus. Try again later", icon=":material/warning:"
            )

        del st.session_state.onsite_service_requests

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                st.session_state.engineer_id
            )

        except Exception as error:
            pass

        time.sleep(3)
        st.rerun()

    if colb.button("Reject Request", icon=":material/close:",
                   use_container_width=True):
        try:
            status_updated = (
                onsite_service_request_collection.assign_service_request_to_admin(
                    service_request_details.get("customer_id"),
                    service_request_id,
                    f"REJECTED_BY_ENGINEER_{st.session_state.engineer_id}",
                )
            )

        except Exception as error:
            pass

        if status_updated:
            st.success("Request removed from queue", icon=":material/cancel:")

        else:
            st.warning(
                "Unable to update staus. Try again later", icon=":material/warning:"
            )

        del st.session_state.onsite_service_requests

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                st.session_state.engineer_id
            )

        except Exception as error:
            pass

        time.sleep(3)
        st.rerun()


@st.dialog("More Options", width="large")
def dialog_view_more_ticket_options(
        service_request_id, service_request_details):
    with st.expander(
        "Verify and Start Ticket Resolution", icon=":material/help:", expanded=True
    ):
        resolution_start_date = service_request_details.get("resolution").get(
            "start_date"
        )

        if resolution_start_date:
            resolution_start_date = datetime.datetime.strptime(
                resolution_start_date,
                "%Y-%m-%d %H:%M:%S",
            ).strftime("%B %d, %Y")

            sac.alert(
                label=f"You have been verified succesfully",
                description=f"The customer has verified you on {resolution_start_date}",
                color="lime",
                icon=True,
            )

        else:
            cola, colb = st.columns([2.5, 1])
            input_otp = bleach.clean(
                cola.text_input(
                    "Enter your Verification OTP",
                    placeholder="Enter your Verification OTP",
                    label_visibility="collapsed",
                )
            )

            if colb.button(
                "Verify with OTP",
                icon=":material/policy:",
                type="primary",
                use_container_width=True,
            ):
                onsite_service_request_collection = OnsiteServiceRequestCollection()
                is_validated, response_code = (
                    onsite_service_request_collection.validate_engineer_verification_otp(
                        service_request_details.get("customer_id"),
                        service_request_id,
                        input_otp,
                    )
                )

                if is_validated:
                    try:
                        try:
                            query_customers = QueryCustomers()

                            customer_name = (
                                query_customers.fetch_customer_details_by_username(
                                    service_request_details.get("customer_id"),
                                    ["first_name", "last_name"],
                                )
                            )

                        except Exception as error:
                            customer_name = {
                                "first_name": "LogIQ",
                                "last_name": "User",
                            }

                        transaction_email_channel = TransactionalEmails()

                        transaction_email_channel.send_onsite_service_request_resolution_started_mail(
                            receiver_full_name=f"{
                                customer_name.get('first_name')} {
                                customer_name.get('last_name')}",
                            receiver_email=service_request_details.get(
                                "customer_contact"
                            ).get("email"),
                            service_request_id=service_request_id,
                            engineer_id=st.session_state.engineer_id,
                            engineer_name=f"{
                                st.session_state.engineer_details.get("first_name")} {
                                st.session_state.engineer_details.get("last_name")}",
                        )

                    except Exception as error:
                        pass

                    try:
                        notification_sms_channel = NotificationSMS()

                        notification_sms_channel.send_onsite_service_request_resolution_started_sms(
                            receivers_phone_number=service_request_details.get(
                                "customer_contact"
                            ).get("phone_number"),
                            service_request_id=service_request_id,
                            engineer_id=st.session_state.engineer_id,
                            engineer_name=f"{
                                st.session_state.engineer_details.get("first_name")} {
                                st.session_state.engineer_details.get("last_name")}",
                        )

                    except Exception as error:
                        pass

                    st.success(
                        "You have been verified successfully", icon=":material/check:"
                    )

                    del st.session_state.onsite_service_requests

                    st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                        st.session_state.engineer_id
                    )

                else:
                    if response_code == 401:
                        st.warning(
                            "You've provided an invalid OTP. Kindly try again!",
                            icon=":material/warning:",
                        )

                    elif response_code == 402:
                        st.warning(
                            "OTP expired or not found. Kindly request customer to generate a new OTP",
                            icon=":material/warning:",
                        )

                    else:
                        st.warning(
                            "Unable to reach server. Kindly try again later!",
                            icon=":material/warning:",
                        )

                time.sleep(3)
                st.rerun()

    with st.expander("Report Unsafe Working Condition", icon=":material/warning:"):
        if service_request_details.get("unsafe_working_condition_reported"):
            sac.alert(
                label=f"Reported Unsafe Working Conditions",
                description=service_request_details.get(
                    "unsafe_working_condition_reported"
                ),
                color="yellow",
                icon=True,
            )

        else:
            working_condition_description = bleach.clean(
                st.text_area(
                    "Describe the unsafe working condition",
                    placeholder="Please provide a detailed description of the unsafe conditions...",
                    label_visibility="collapsed",
                )
            )
            cola, _ = st.columns([1, 3])

            if cola.button("Report to Team", icon=":material/report:"):
                onsite_service_request_collection = OnsiteServiceRequestCollection()

                response = (
                    onsite_service_request_collection.report_unsafe_working_condition(
                        service_request_details.get("customer_id"),
                        service_request_id,
                        working_condition_description,
                    )
                )

                if response:
                    st.success(
                        "Unsafe working condition reported successfully",
                        icon=":material/check:",
                    )
                    del st.session_state.onsite_service_requests

                    st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                        st.session_state.engineer_id
                    )

                else:
                    st.warning(
                        "Unable to report unsafe working condition. Try again later",
                        icon=":material/warning:",
                    )

                time.sleep(3)
                st.rerun()


@st.dialog("Service Request Details", width="large")
def dialog_view_service_request_details(
    service_request_id, service_request_details, is_approved=True
):
    cola, colb = st.columns([2, 1])

    with cola:
        st.markdown(
            f"""
            <P class="p-vsrd-1">
                Request Id: {service_request_id}
            </P>
            <H1 class="h1-vsrd-1">
                {service_request_details.get('request_title')}
            </H1>
            """,
            unsafe_allow_html=True,
        )

    with colb:
        st.markdown(
            f"""
            <H2 class="h2-vsrd-2" align='right'>
                <B>Status:
                    {service_request_details.get('ticket_status').capitalize()}
                </B>
            </P>
            """,
            unsafe_allow_html=True,
        )

    cola, _, colb = st.columns([1, 0.05, 4])

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
            {service_request_details.get('appliance_details').get('brand')}
            {service_request_details.get('appliance_details').get('category')}
            &nbsp;• &nbsp;Model Number:
            {service_request_details.get('appliance_details').get('model_number')}
            """,
            unsafe_allow_html=True,
        )

        st.write(" ")

        try:
            request_created_on = datetime.datetime.strptime(
                service_request_details.get("created_on"),
                "%Y-%m-%d %H:%M:%S",
            )
        except Exception as error:
            pass

        if is_approved:
            try:
                engineer_assigned_on = datetime.datetime.strptime(
                    service_request_details.get("engineer_assigned_on"),
                    "%Y-%m-%d %H:%M:%S",
                )
            except Exception as error:
                pass

            st.markdown(
                f"""
                📆 Request created on {request_created_on.strftime('%B %d, %Y (%A)')}
                <BR>
                🛠️ This ticket was assigned to you on {engineer_assigned_on.strftime('%B %d, %Y (%A)')}
                """,
                unsafe_allow_html=True,
            )

        else:
            st.markdown(
                f"""
                📆 Request created on {request_created_on.strftime('%B %d, %Y (%A)')}
                <BR>
                📥 Ticket assigned by system. Approve to add this to your work queue.
                """,
                unsafe_allow_html=True,
            )

    st.write(" ")
    selected_tab = sac.tabs(
        [
            sac.TabsItem(label="Request Details"),
            sac.TabsItem(label="Appliance Details"),
            sac.TabsItem(label="Ticket Activity"),
        ],
        variant="outline",
    )

    if selected_tab == "Request Details":
        colx, coly = st.columns([3, 1.5])

        with colx:
            st.markdown(
                f"🆔 <B>Request Type:</B> {
                    service_request_details.get('request_type')}",
                unsafe_allow_html=True,
            )

        with coly:
            st.markdown(
                f"<P align='right'>#️⃣ <B>Serial No.:</B> {
                    service_request_details.get('appliance_details').get('serial_number')}</P>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <P align='left'>
                🈺 <B>Request Description:</B>
                <BR>
                {service_request_details.get('description')}
            </P>
            """,
            unsafe_allow_html=True,
        )

    elif selected_tab == "Appliance Details":
        st.markdown(
            f"🈳 <B>Appliance Name:</B> {
                service_request_details.get('appliance_details').get('brand')} {
                service_request_details.get('appliance_details').get('sub_category')}",
            unsafe_allow_html=True,
        )

        cola, colb, colc = st.columns([1.1, 1.1, 1])

        with cola:
            st.markdown(
                f"""
                🔢 <B>Serial Number:</B>
                {service_request_details.get('appliance_details').get('serial_number')}
                """,
                unsafe_allow_html=True,
            )

        with colb:
            st.markdown(
                f"""
                🏷️ <B>Model Number:</B>
                {service_request_details.get('appliance_details').get('model_number')}
                """,
                unsafe_allow_html=True,
            )

        with colc:
            st.markdown(
                f"""
                📅 <B>Purchased On:</B>
                {service_request_details.get('appliance_details').get('purchase_date')}
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            ✅ {service_request_details.get('appliance_details').get('warranty_period')}-
            Month Manufacturer Warranty,
            Expires on {service_request_details.get('appliance_details').get('warranty_expiration')}
            (Purchased from {service_request_details.get('appliance_details').get('seller')})
            """,
            unsafe_allow_html=True,
        )

        customer_records_bucket = CustomerRecordsBucket()
        cola, colb, _ = st.columns([1.4, 0.3, 1.7])

        with cola:
            try:
                warranty_certificate_url = (
                    customer_records_bucket.fetch_warranty_certificate_url(
                        customer_id=service_request_details.get("customer_id"),
                        serial_number=service_request_details.get(
                            "appliance_details"
                        ).get("serial_number"),
                        sub_category=service_request_details.get(
                            "appliance_details"
                        ).get("sub_category"),
                    )
                )

                st.link_button(
                    "Download Warranty Certificate",
                    url=warranty_certificate_url,
                    use_container_width=True,
                    icon=":material/license:",
                )

            except Exception as error:
                pass

        with colb:
            try:
                product_invoice_url = customer_records_bucket.fetch_product_invoice_url(
                    customer_id=service_request_details.get("customer_id"),
                    serial_number=service_request_details.get("appliance_details").get(
                        "serial_number"
                    ),
                    sub_category=service_request_details.get("appliance_details").get(
                        "sub_category"
                    ),
                )

                st.link_button(
                    ":material/receipt:",
                    url=product_invoice_url,
                    use_container_width=True,
                )

            except Exception as error:
                pass

    if selected_tab == "Ticket Activity":

        @st.cache_data(show_spinner=False)
        def fetch_and_cache_ticket_activity(customer_id, request_id):
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            return onsite_service_request_collection.fetch_service_request_activity(
                customer_id, request_id
            )

        ticket_activity = fetch_and_cache_ticket_activity(
            service_request_details.get("customer_id"),
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


@st.dialog("Directions to Customer Address", width="large")
def display_directions_to_customer_location(
    origin, destination, contact_number="Not Provided", email_id="Not Provided"
):
    st.markdown(
        f"""
        <P>
            <B>🗺️ Customer Address: </B>
            <BR>{destination}<BR><BR>
            <B>📨 E-mail Id: </B>{email_id}
            &nbsp;&nbsp;&nbsp;&nbsp;
            <B>☎️ Phone Number: </B>(+91) {contact_number}
        </P>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Finding the best route...", show_time=True):
        loc_services = LocationServices()
        map_obj = loc_services.display_route_with_folium(origin, destination)

    st.markdown(f"<H4>Route Preview:</H4>", unsafe_allow_html=True)

    folium_static(map_obj)


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


# if st.session_state.themes["current_theme"] == "dark":
# st.logo("assets/logos/logiq_logo_dark.png", size='large')
# else: st.logo("assets/logos/logiq_logo_light.png", size='large')


if __name__ == "__main__":
    if st.session_state.engineer_id:

        @st.cache_data(show_spinner=False)
        def get_engineer_details(full_details=False):
            query_engineers = QueryEngineers()
            engineer_details = query_engineers.fetch_engineer_details_by_id(
                st.session_state.engineer_id
            )

            st.session_state.engineer_details = engineer_details
            return st.session_state.engineer_details

        get_engineer_details(full_details=False)

        with st.sidebar:
            selected_menu_item = sac.menu(
                [
                    sac.MenuItem(
                        "My Dashboard",
                        icon="grid",
                    ),
                    sac.MenuItem(
                        "View Requests",
                        icon="inboxes",
                    ),
                    sac.MenuItem(
                        "LogIQ Chatbot",
                        icon="chat-square-text",
                    ),
                    sac.MenuItem(" ", disabled=True),
                    sac.MenuItem(type="divider"),
                ],
                open_all=True,
            )

            sidebar_container = st.container(height=240, border=False)

        if selected_menu_item == "My Dashboard":
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_onsite_service_requests(engineer_id):
                st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                    engineer_id
                )

                assigned_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (service_request.get("assignment_status") == "confirmed") and (
                        service_request.get("ticket_status") != "resolved"
                    ):
                        assigned_count += 1
                st.session_state.ticket_counts["assigned"] = assigned_count

                new_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (
                        service_request.get("assignment_status")
                        == "pending_confirmation"
                    ):
                        new_count += 1
                st.session_state.ticket_counts["pending"] = new_count

                resolved_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (service_request.get("assignment_status") == "confirmed") and (
                        service_request.get("ticket_status") == "resolved"
                    ):
                        resolved_count += 1
                st.session_state.ticket_counts["resolved"] = resolved_count

            fetch_and_cache_onsite_service_requests(
                st.session_state.engineer_id)

            with sidebar_container:
                st.markdown("<B>Announcements</B>", unsafe_allow_html=True)
                colx, coly, colz = st.columns(
                    [0.77, 2.3, 0.7], vertical_alignment="center"
                )

                with colx:
                    st.image(
                        "assets/app_graphics/maintenance_banner.png",
                        use_container_width=True,
                    )
                with coly:
                    st.markdown(
                        """
                        <B>Maintenance Break</B>
                        <BR>
                        Scheduled on March 05
                        """,
                        unsafe_allow_html=True,
                    )

                with colz:
                    if st.button(
                        "",
                        icon=":material/open_in_new:",
                        use_container_width=True,
                        key="_announcement_1",
                    ):
                        st.toast("Announcement currently unavailable")

                colx, coly, colz = st.columns(
                    [0.77, 2.3, 0.7], vertical_alignment="center"
                )

                with colx:
                    st.image(
                        "assets/app_graphics/break_banner.png",
                        use_container_width=True,
                    )
                with coly:
                    st.markdown(
                        """
                        <B>Training Reminder</B>
                        <BR>
                        Sessions on Safety Tips
                        """,
                        unsafe_allow_html=True,
                    )

                with colz:
                    if st.button(
                        "",
                        icon=":material/open_in_new:",
                        use_container_width=True,
                        key="_announcement_2",
                    ):
                        st.toast("Announcement currently unavailable")

                sac.divider(align="center")

            with st.sidebar:
                st.write(" ")
                st.markdown("<BR><BR>", unsafe_allow_html=True)

                if st.button(
                    "Manage Account",
                    icon=":material/manage_accounts:",
                    use_container_width=True,
                ):
                    dialog_manage_account()

            @st.cache_data(show_spinner=False)
            def get_engineer_name(full_name=True):
                query_engineers = QueryEngineers()

                engineer_details = query_engineers.fetch_engineer_details_by_id(
                    st.session_state.engineer_id, ["first_name", "last_name"]
                )

                if full_name:
                    return (
                        engineer_details.get("first_name")
                        + " "
                        + engineer_details.get("last_name")
                    )

                return engineer_details.get("first_name")

            engineer_name = get_engineer_name(full_name=True)

            morning_start = timedelta(hours=5)
            afternoon_start = timedelta(hours=12)
            evening_start = timedelta(hours=17)
            night_start = timedelta(hours=21)

            ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)
            current_time = timedelta(
                hours=ist_now.hour, minutes=ist_now.minute)

            if morning_start <= current_time < afternoon_start:
                greeting = "Good Morning"
            elif afternoon_start <= current_time < evening_start:
                greeting = "Good Afternoon"
            elif evening_start <= current_time < night_start:
                greeting = "Good Evening"
            else:
                greeting = "Hello"

            ribbon_col_1, ribbon_col_2, ribbon_col_3, ribbon_col_4 = st.columns(
                [4.2, 1, 0.4, 0.4], vertical_alignment="center"
            )

            with ribbon_col_1:
                st.markdown(
                    f"<H4>{greeting}, {str(engineer_name)}! 👋</H4>",
                    unsafe_allow_html=True,
                )

            with ribbon_col_2:
                if st.button(
                    "Spare Parts", icon=":material/store:", use_container_width=True
                ):
                    st.toast("Marketplace is currently unavailable")

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
                    help="Theme",
                    on_click=change_streamlit_theme,
                )

            with ribbon_col_4:
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

            with st.container(border=False):
                tab_request_assignment_status = sac.tabs(
                    [
                        sac.TabsItem(label="Assigned", icon="person-gear"),
                        sac.TabsItem(label="New", icon="person-add"),
                        sac.TabsItem(label="Resolved", icon="person-check"),
                    ],
                    variant="outline",
                )

                if tab_request_assignment_status.lower() == "assigned":
                    assigned_count = 0

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get(
                                "assignment_status") == "confirmed"
                        ) and (service_request.get("ticket_status") != "resolved"):
                            assigned_count += 1

                            with stylable_container(
                                key=f"container_with_border_{assigned_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns(
                                    [0.85, 2.71, 1.5])

                                with cola:
                                    st.image(
                                        service_request.get("appliance_details").get(
                                            "appliance_image_url"
                                        ),
                                        use_container_width=True,
                                    )

                                with colb:
                                    colx, coly = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{
                                                service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {service_request.get('appliance_details').get('sub_category')} &nbsp;•&nbsp; {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: {service_request.get('ticket_status').capitalize()} &nbsp
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
                                            icon=":material/location_on:",
                                            use_container_width=True,
                                            key=f"_edit_service_reques.t_{
                                                service_request.get('request_id')}",
                                        ):
                                            try:
                                                st.toast(
                                                    "Finding the best route")

                                                query_engineers = QueryEngineers()

                                                engineer_address_data = query_engineers.fetch_engineer_details_by_id(
                                                    st.session_state.engineer_id,
                                                    [
                                                        "street",
                                                        "city",
                                                        "district",
                                                        "state",
                                                        "zip_code",
                                                    ],
                                                )

                                                engineer_address = f"""{
                                                    engineer_address_data.get("street")}, {
                                                    engineer_address_data.get("city")}, {
                                                    engineer_address_data.get("district")}, {
                                                    engineer_address_data.get("state")} - {
                                                    engineer_address_data.get("zip_code")}"""

                                                customer_address = f"""{
                                                    service_request.get("address").get("street")}, {
                                                    service_request.get("address").get("city")}, {
                                                    service_request.get("address").get("state")} - {
                                                    service_request.get("address").get("zipcode")}"""

                                                display_directions_to_customer_location(
                                                    engineer_address,
                                                    customer_address,
                                                    service_request.get(
                                                        "customer_contact"
                                                    ).get("phone_number"),
                                                    service_request.get(
                                                        "customer_contact"
                                                    ).get("email"),
                                                )

                                            except Exception as error:
                                                st.toast(
                                                    "Location services are currently unavailable"
                                                )

                                    with coly:
                                        if st.button(
                                            "View Details",
                                            icon=":material/page_info:",
                                            use_container_width=True,
                                            key=f"_recent_service_request_deta.ils_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_view_service_request_details(
                                                service_request.get(
                                                    "request_id"),
                                                service_request,
                                            )

                    if assigned_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No Assigned Requests",
                            description="You currently have no requests assigned to you",
                            status="empty",
                        )

                elif tab_request_assignment_status.lower() == "new":
                    new_count = 0

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get("assignment_status")
                            == "pending_confirmation"
                        ):
                            new_count += 1

                            with stylable_container(
                                key=f"container_with_border_{new_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns(
                                    [0.85, 2.71, 1.5])

                                with cola:
                                    st.image(
                                        service_request.get("appliance_details").get(
                                            "appliance_image_url"
                                        ),
                                        use_container_width=True,
                                    )

                                with colb:
                                    colx, coly = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{
                                                service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {service_request.get('appliance_details').get('sub_category')} • {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: Pending &nbsp
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
                                            icon=":material/check_circle:",
                                            use_container_width=True,
                                            key=f"_edit_service_reques.t_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_review_service_request(
                                                service_request.get(
                                                    "request_id"),
                                                service_request,
                                            )

                                    with coly:
                                        if st.button(
                                            "View Details",
                                            icon=":material/page_info:",
                                            use_container_width=True,
                                            key=f"_recent_service_request_deta.ils_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_view_service_request_details(
                                                service_request.get(
                                                    "request_id"),
                                                service_request,
                                                is_approved=False,
                                            )

                    if new_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No New Requests",
                            description="No new requests have been assigned to you",
                            status="empty",
                        )

                else:
                    resolved_count = 0

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get(
                                "assignment_status") == "confirmed"
                        ) and (service_request.get("ticket_status") == "resolved"):
                            resolved_count += 1

                            with stylable_container(
                                key=f"container_with_border_{resolved_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns(
                                    [0.85, 2.71, 1.5])

                                with cola:
                                    st.image(
                                        service_request.get("appliance_details").get(
                                            "appliance_image_url"
                                        ),
                                        use_container_width=True,
                                    )

                                with colb:
                                    colx, coly = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{
                                                service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {service_request.get('appliance_details').get('sub_category')} • {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: {service_request.get('ticket_status').capitalize()} &nbsp
                                                </B>
                                            </font>
                                        </P>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                    st.write(" ")

                                    colx, coly = st.columns([0.9, 3])
                                    with colx:
                                        st.link_button(
                                            "",
                                            url="",
                                            icon=":material/description:",
                                            help="Invoice",
                                            use_container_width=True,
                                        )

                                    with coly:
                                        if st.button(
                                            "Resolution Notes",
                                            icon=":material/notes:",
                                            use_container_width=True,
                                            key=f"_recent_service_request_deta.ils_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_display_resolution_details(
                                                service_request
                                            )

                    if resolved_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No Resolved Requests",
                            description="You have no service requests marked resolved",
                            status="empty",
                        )

        elif selected_menu_item == "View Requests":
            open_service_requests = {}

            for service_request in st.session_state.onsite_service_requests:
                if (service_request.get("assignment_status") == "confirmed") and (
                    service_request.get("ticket_status") != "resolved"
                ):
                    open_service_requests[service_request.get("request_id")] = (
                        service_request
                    )

            with sidebar_container:
                request_id_to_view = st.selectbox(
                    "Request Id",
                    open_service_requests.keys(),
                    index=None,
                    placeholder="Select Request Id to View",
                )

                if request_id_to_view:
                    st.markdown(
                        f"""
                        <style>
                            a {{
                                color: {st.session_state.themes["dark" if st.session_state.themes["current_theme"] == "light" else "light"]["theme.textColor"]} !important;
                                text-decoration: none; /* Optional: Removes underline */
                            }}

                            a:hover, a:visited, a:active {{
                                color: {st.session_state.themes["dark" if st.session_state.themes["current_theme"] == "light" else "light"]["theme.textColor"]} !important;
                            }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    @st.cache_data(show_spinner=False)
                    def get_service_manual(request_id):
                        service_manual_bucket = ServiceManualBucket()
                        service_manual_url = service_manual_bucket.fetch_service_manual_url(
                            f"{
                                open_service_requests.get(request_id).get("appliance_details").get("category").lower().replace(
                                    ' ',
                                    '_').replace(
                                    '-',
                                    '_').replace(
                                    '/',
                                    '_')}/{
                                open_service_requests.get(request_id).get("appliance_details").get("sub_category").lower().replace(
                                    " ",
                                    "_").replace(
                                    "-",
                                    "_").replace(
                                    "/",
                                    "_")}_service_guide.pdf"
                        )
                        return service_manual_url

                    service_manual_url = get_service_manual(request_id_to_view)

                    @st.cache_data(show_spinner=False)
                    def get_warranty_certificate_url(request_id):
                        customer_records_bucket = CustomerRecordsBucket()

                        try:
                            warranty_certificate_url = (
                                customer_records_bucket.fetch_warranty_certificate_url(
                                    open_service_requests.get(request_id).get(
                                        "customer_id"
                                    ),
                                    open_service_requests.get(request_id)
                                    .get("appliance_details")
                                    .get("serial_number"),
                                    open_service_requests.get(request_id)
                                    .get("appliance_details")
                                    .get("sub_category"),
                                )
                            )

                        except Exception as error:
                            warranty_certificate_url = "www.example.com"
                        return warranty_certificate_url

                    warranty_certificate_url = get_warranty_certificate_url(
                        request_id_to_view
                    )

                    colx, coly = st.columns(
                        [0.77, 3], vertical_alignment="center")

                    with colx:
                        st.image(
                            "assets/app_graphics/troubleshoot_guide_banner.png",
                            use_container_width=True,
                        )

                    with coly:
                        st.markdown(
                            f"""
                            <B>Model: SAV42716</B><BR>
                            <A href='{service_manual_url}'>
                            Launch Troubleshooting Guide
                            </A>""",
                            unsafe_allow_html=True,
                        )

                    colx, coly = st.columns(
                        [0.77, 3], vertical_alignment="center")

                    with colx:
                        st.image(
                            "assets/app_graphics/warranty_document_banner.png",
                            use_container_width=True,
                        )
                    with coly:
                        st.markdown(
                            f"""
                            <B>Serial No.: 218294380928</B><BR>
                            <A href='{warranty_certificate_url}'>
                            Customers Warranty Document
                            </A>
                            """,
                            unsafe_allow_html=True,
                        )

                else:
                    sac.alert(
                        label=f"Trouble Viewing Content?",
                        description="Press **C** to clear cache then **R** to refresh page.",
                        color="orange",
                        icon=True,
                    )
                    st.markdown("<BR><BR>", unsafe_allow_html=True)

            with st.sidebar:
                st.write(" ")
                st.markdown("<BR><BR>", unsafe_allow_html=True)

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

            if request_id_to_view:
                cola, colb = st.columns([2.75, 2], vertical_alignment="center")

                with cola:
                    st.markdown(
                        f"""
                        <P class="p-ticket-details-ribbon-title">
                            Request Id: {request_id_to_view}
                        </P>
                        <H4 class="h4-ticket-details-ribbon-title">
                            {open_service_requests.get(request_id_to_view).get('request_title')}
                        </H1>
                        """,
                        unsafe_allow_html=True,
                    )

                with colb:
                    colx, coly, colz = st.columns(
                        [1, 2.75, 2.75], vertical_alignment="center"
                    )

                    with colx:
                        if st.button(
                            "",
                            icon=":material/format_list_bulleted:",
                            use_container_width=True,
                        ):
                            dialog_view_more_ticket_options(
                                request_id_to_view,
                                open_service_requests.get(request_id_to_view),
                            )

                    with coly:
                        if st.button(
                            "Commute",
                            icon=":material/location_on:",
                            use_container_width=True,
                        ):
                            st.toast("Finding the best route")

                            query_engineers = QueryEngineers()

                            engineer_address_data = (
                                query_engineers.fetch_engineer_details_by_id(
                                    st.session_state.engineer_id,
                                    ["street", "city", "district",
                                        "state", "zip_code"],
                                )
                            )

                            engineer_address = f"""
                            {engineer_address_data.get("street")}, {engineer_address_data.get("city")},
                            {engineer_address_data.get("district")},
                            {engineer_address_data.get("state")} - {engineer_address_data.get("zip_code")}
                            """

                            customer_address = f"""
                            {open_service_requests.get(request_id_to_view).get("address").get("street")},
                            {open_service_requests.get(request_id_to_view).get("address").get("city")},
                            {open_service_requests.get(request_id_to_view).get("address").get("state")} -
                            {open_service_requests.get(request_id_to_view).get("address").get("zipcode")}
                            """

                            display_directions_to_customer_location(
                                engineer_address,
                                customer_address,
                                contact_number=open_service_requests.get(
                                    request_id_to_view
                                )
                                .get("customer_contact")
                                .get("phone_number"),
                                email_id=open_service_requests.get(
                                    request_id_to_view)
                                .get("customer_contact")
                                .get("email"),
                            )

                    with colz:
                        if st.button(
                            "Resolve",
                            icon=":material/done_all:",
                            type="primary",
                            use_container_width=True,
                        ):
                            dialog_resolve_service_request(
                                request_id_to_view,
                                open_service_requests.get(request_id_to_view),
                            )

                cola, _, colb = st.columns([0.9, 0.1, 4])

                with cola:
                    st.image(
                        open_service_requests.get(request_id_to_view)
                        .get("appliance_details")
                        .get("appliance_image_url"),
                        use_container_width=True,
                    )

                with colb:
                    colx, coly = st.columns([2.5, 1])

                    with colx:
                        st.markdown(
                            f"""
                            <H4 class="h2-ticket-details-appliance-title">
                                {open_service_requests.get(request_id_to_view).get('appliance_details').get('sub_category')}</H2>{open_service_requests.get(request_id_to_view).get('appliance_details').get('brand')} (Model No.: {open_service_requests.get(request_id_to_view).get('appliance_details').get('model_number')}) • Serial Number: {open_service_requests.get(request_id_to_view).get('appliance_details').get('serial_number')}
                            </H4>
                            """,
                            unsafe_allow_html=True,
                        )

                    with coly:
                        st.markdown(
                            f"""
                            <BR>
                            <H5 class="h5-ticket-details-status" align='right'>
                                Status: {open_service_requests.get(request_id_to_view).get('ticket_status').capitalize()}
                            """,
                            unsafe_allow_html=True,
                        )

                    request_created_on = datetime.datetime.strptime(
                        open_service_requests.get(
                            request_id_to_view).get("created_on"),
                        "%Y-%m-%d %H:%M:%S",
                    )

                    warranty_expiry_date = datetime.datetime.strptime(
                        open_service_requests.get(request_id_to_view)
                        .get("appliance_details")
                        .get("warranty_expiration"),
                        "%Y-%m-%d",
                    )

                    st.markdown(
                        f"""<BR>
                        📅 Request Created On: {request_created_on.strftime('%B %d, %Y (%A)')}<BR>
                        ✅ {open_service_requests.get(request_id_to_view).get('appliance_details').get('warranty_period')}-month
                        warranty, expires on {warranty_expiry_date.strftime('%B %d, %Y')}
                        (Purchased from {open_service_requests.get(request_id_to_view).get('appliance_details').get('seller')})
                        """,
                        unsafe_allow_html=True,
                    )

                st.write(" ")
                selected_tab = sac.tabs(
                    [
                        sac.TabsItem(label="Request Details"),
                        sac.TabsItem(label="Ticket Activity"),
                        sac.TabsItem(label="Appliance History"),
                        sac.TabsItem(label="Parts Replaced", disabled=True),
                    ],
                    variant="outline",
                )

                if selected_tab == "Request Details":
                    cola, _, colb = st.columns([2.2, 0.001, 0.75])

                    with cola:
                        st.markdown(
                            f"""
                            <B>🈺 Address and Contact: </B><BR>
                            {open_service_requests.get(request_id_to_view).get("address").get("street")},
                            {open_service_requests.get(request_id_to_view).get("address").get("city")},
                            {open_service_requests.get(request_id_to_view).get("address").get("state")} -
                            {open_service_requests.get(request_id_to_view).get("address").get("zipcode")}
                            (Phone No.: {open_service_requests.get(request_id_to_view).get('customer_contact').get('phone_number')})
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            f"""
                            <P align='left'>
                                ▶️ <B>Request Description:</B>
                                <BR>
                                {open_service_requests.get(request_id_to_view).get("description")}
                            </P>
                            """,
                            unsafe_allow_html=True,
                        )

                    with colb:
                        st.write(" ")
                        with st.container(border=False):
                            colx, coly = st.columns([1, 3])

                            with colx:
                                st.image(
                                    "assets/placeholders/trident_yellow.png",
                                    use_container_width=True,
                                )

                            with coly:
                                st.markdown(
                                    f"""
                                    <H6 class="h6-profile-snapshot-metric">
                                        Requested On
                                    </H6>
                                    <P class="p-profile-snapshot-metric">
                                        {request_created_on.strftime('%B %d, %Y')}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            colx, coly = st.columns([1, 3])

                            request_assigned_on = datetime.datetime.strptime(
                                open_service_requests.get(request_id_to_view).get(
                                    "engineer_assigned_on"
                                ),
                                "%Y-%m-%d %H:%M:%S",
                            )

                            with colx:
                                st.image(
                                    "assets/placeholders/trident_green.png",
                                    use_container_width=True,
                                )

                            with coly:
                                st.markdown(
                                    f"""
                                    <H6 class="h6-profile-snapshot-metric">
                                        Assigned On
                                    </H6>
                                    <P class="p-profile-snapshot-metric">
                                        {request_assigned_on.strftime('%B %d, %Y')}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            colx, coly = st.columns([1, 3])

                            sla_expiry_on = request_assigned_on + \
                                timedelta(days=5)

                            with colx:
                                st.image(
                                    "assets/placeholders/trident_red.png",
                                    use_container_width=True,
                                )

                            with coly:
                                st.markdown(
                                    f"""
                                    <H6 class="h6-profile-snapshot-metric">
                                        SLA Expiry On
                                    </H6>
                                    <P class="p-profile-snapshot-metric">
                                        {sla_expiry_on.strftime('%B %d, %Y')}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                elif selected_tab == "Ticket Activity":

                    @st.cache_data(show_spinner=False)
                    def fetch_and_cache_ticket_activity(
                            customer_id, request_id):
                        onsite_service_request_collection = (
                            OnsiteServiceRequestCollection()
                        )
                        return onsite_service_request_collection.fetch_service_request_activity(
                            customer_id, request_id
                        )

                    with st.form(
                        key="_form_post_ticket_activity",
                        clear_on_submit=True,
                        border=False,
                    ):
                        cola, colb = st.columns(
                            [5, 1], vertical_alignment="bottom")

                        with cola:
                            engineer_notes = bleach.clean(
                                st.text_area(
                                    "Enter Engineer notes",
                                    placeholder="Share new update to post...",
                                    label_visibility="collapsed",
                                    height=80,
                                )
                            )

                        with colb:
                            if st.form_submit_button(
                                "Post Update",
                                icon=":material/library_add:",
                                use_container_width=True,
                            ):
                                if len(engineer_notes) > 0:
                                    onsite_service_request_collection = (
                                        OnsiteServiceRequestCollection()
                                    )

                                    onsite_service_request_collection.add_service_request_activity(
                                        open_service_requests.get(
                                            request_id_to_view
                                        ).get("customer_id"),
                                        request_id_to_view,
                                        "Engineer",
                                        engineer_notes,
                                    )

                                    try:
                                        fetch_and_cache_ticket_activity.clear()
                                    except Exception as error:
                                        pass

                                    del st.session_state.onsite_service_requests

                                    st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                                        st.session_state.engineer_id
                                    )

                                    st.toast("Update posted!")
                                    time.sleep(3)
                                    st.rerun()

                                else:
                                    alert = st.warning(
                                        "Enter notes to add", icon=":material/warning:"
                                    )
                                    time.sleep(3)
                                    alert.empty()

                    ticket_activity = fetch_and_cache_ticket_activity(
                        open_service_requests.get(request_id_to_view).get(
                            "customer_id"
                        ),
                        request_id_to_view,
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

                    @st.cache_data(show_spinner=False)
                    def fetch_and_cache_appliance_service_request_history(
                        customer_id, serial_number
                    ):
                        onsite_service_request_collection = (
                            OnsiteServiceRequestCollection()
                        )
                        appliance_service_request_history = onsite_service_request_collection.fetch_resolution_details_by_appliance_serial_number(
                            customer_id, serial_number
                        )

                        if request_id_to_view in appliance_service_request_history:
                            del appliance_service_request_history[request_id_to_view]

                        return appliance_service_request_history

                    appliance_service_request_history = (
                        fetch_and_cache_appliance_service_request_history(
                            open_service_requests.get(request_id_to_view).get(
                                "customer_id"
                            ),
                            open_service_requests.get(request_id_to_view)
                            .get("appliance_details")
                            .get("serial_number"),
                        )
                    )

                    if len(appliance_service_request_history) == 0:
                        st.markdown("<BR>", unsafe_allow_html=True)
                        sac.result(
                            label="No History Available",
                            description="This appliance has no recorded service history",
                            status="empty",
                        )

                    else:
                        cola, _, colb = st.columns(
                            [0.33, 0.44, 0.16], vertical_alignment="center"
                        )

                        with cola:
                            service_request_resolution_details = st.selectbox(
                                "Select Request Id",
                                appliance_service_request_history.keys(),
                                label_visibility="collapsed",
                                index=None,
                                placeholder="Request Id",
                            )

                        with colb:
                            button_view_resolution_history = st.button(
                                "View Details",
                                icon=":material/notes:",
                                use_container_width=True,
                            )

                        if button_view_resolution_history:
                            cola, colb = st.columns(
                                [0.4, 0.15], vertical_alignment="bottom"
                            )

                            with cola:
                                st.write(" ")
                                st.markdown(
                                    f"""
                                    <H5>Service Request Description</H5>

                                    <P>
                                        <B>Request Title:</B>
                                        {appliance_service_request_history.get(service_request_resolution_details).get('request_title')}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            request_raised_on = datetime.datetime.strptime(
                                appliance_service_request_history.get(
                                    service_request_resolution_details
                                ).get("created_on"),
                                "%Y-%m-%d %H:%M:%S",
                            ).strftime("%B %d, %Y")

                            with colb:
                                st.markdown(
                                    f"""
                                    <P align='right'>
                                        <B>Raised on:</B> {request_raised_on}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            st.markdown(
                                f"""
                                <P align='left'>
                                    <B>Description:</B>
                                    {appliance_service_request_history.get(service_request_resolution_details).get('description')}
                                </P>
                                """,
                                unsafe_allow_html=True,
                            )

                            sac.divider(align="center", color="#181818")
                            cola, colb = st.columns(
                                [0.1, 0.15], vertical_alignment="bottom"
                            )

                            with cola:
                                st.markdown(
                                    "<H5>Engineer Activity and Resolution</H5>",
                                    unsafe_allow_html=True,
                                )

                            resolution_start_date = datetime.datetime.strptime(
                                appliance_service_request_history.get(
                                    service_request_resolution_details
                                ).get("start_date"),
                                "%Y-%m-%d %H:%M:%S",
                            ).strftime("%B %d, %Y")

                            resolution_end_date = datetime.datetime.strptime(
                                appliance_service_request_history.get(
                                    service_request_resolution_details
                                ).get("end_date"),
                                "%Y-%m-%d %H:%M:%S",
                            ).strftime("%B %d, %Y")

                            with colb:
                                st.markdown(
                                    f"""
                                    <P align='right'>
                                        {resolution_start_date} - {resolution_end_date}
                                    </P>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            st.markdown(
                                f"""
                                <P align='left'>
                                    {appliance_service_request_history.get(service_request_resolution_details).get('action_performed', '')}
                                </P>

                                <P align='left'>
                                    {appliance_service_request_history.get(service_request_resolution_details).get('additional_notes', '')}
                                </P>
                                """,
                                unsafe_allow_html=True,
                            )

                        else:
                            sac.alert(
                                label=f"Selet a Request ID",
                                description="Choose a Request ID from the list to proceed with your request",
                                color="yellow",
                                icon=True,
                            )

            else:
                st.markdown("<BR>" * 6, unsafe_allow_html=True)
                sac.result(
                    label="Selet a Request ID",
                    description="Choose a Request ID from the list to proceed with your request",
                    status="empty",
                )

        else:
            with sidebar_container:
                if not st.session_state.cache_model_number:
                    available_sub_categories = (
                        st.session_state.distinct_appliance_details.keys()
                    )

                    input_sub_category = st.selectbox(
                        "Select Appliance",
                        available_sub_categories,
                        index=None,
                        placeholder="Select Appliance",
                        label_visibility="collapsed",
                    )

                    available_brands = (
                        st.session_state.distinct_appliance_details.get(
                            input_sub_category
                        ).keys()
                        if input_sub_category
                        else []
                    )

                    input_brand = st.selectbox(
                        "Select the Brand",
                        available_brands,
                        index=None,
                        placeholder="Select the Brand",
                        label_visibility="collapsed",
                    )

                    available_models = (
                        st.session_state.distinct_appliance_details.get(
                            input_sub_category
                        ).get(input_brand)
                        if input_brand
                        else []
                    )

                    input_model_number = st.selectbox(
                        "Select the Model",
                        available_models,
                        index=None,
                        placeholder="Select the Model",
                        label_visibility="collapsed",
                    )

                    if st.button(
                        "Configure Chatbot",
                        # icon=":material/sync_alt:",
                        use_container_width=True,
                        disabled=not (input_model_number),
                    ):
                        set_cache_model_number(
                            input_brand, input_sub_category, input_model_number
                        )
                        st.rerun()

            if st.session_state.cache_model_number:
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                if "gemini_flash" not in st.session_state:
                    st.toast(
                        f"Configuring chatbot for {
                            st.session_state.cache_model_number}. This may take a minute."
                    )

                    if st.session_state.themes["current_theme"] == "dark":
                        preloader_path = "assets/preloaders/work_in_progress_dark.gif"
                    else:
                        preloader_path = "assets/preloaders/work_in_progress_light.gif"

                    with open(preloader_path, "rb") as f:
                        image_data = f.read()
                        encoded_image = base64.b64encode(image_data).decode()

                        st.write(" ")
                        preloader_work_in_progress = st.markdown(
                            f'<BR><BR><div class="rounded-image"><img src="data:image/png;base64,{encoded_image}"></div>',
                            unsafe_allow_html=True,
                        )

                    with preloader_work_in_progress:
                        configuration_information = f"""
                        Configuring chatbot for
                        {st.session_state.cache_brand} {st.session_state.cache_sub_category} ({st.session_state.cache_model_number})
                        """

                        warning_configuring_chatbot = st.sidebar.info(
                            configuration_information, icon=":material/info:"
                        )

                        query_appliances = Appliances()

                        if "cache_category" not in st.session_state:
                            st.session_state.cache_category = (
                                query_appliances.fetch_category_by_sub_caegory(
                                    st.session_state.cache_sub_category
                                )
                            )

                        try:
                            st.session_state.gemini_flash = build_context_cache(
                                st.session_state.cache_brand,
                                st.session_state.cache_category,
                                st.session_state.cache_sub_category,
                                st.session_state.cache_model_number,
                            )

                            st.session_state.flag_use_context_cache = True

                        except Exception as error:
                            service_manual_uri = f"""gs://service_manual_bucket/{
                                st.session_state.cache_category.lower().replace(
                                    " ",
                                    "_").replace(
                                    "-",
                                    "_").replace(
                                    "/",
                                    "_")}/{
                                st.session_state.cache_sub_category.lower().replace(
                                    " ",
                                    "_").replace(
                                    "-",
                                    "_").replace(
                                    "/",
                                    "_")}_service_guide.pdf"""

                            service_engineer_chatbot = ServiceEngineerChatbot()

                            st.session_state.gemini_flash = (
                                service_engineer_chatbot.construct_flash_model(
                                    st.session_state.cache_brand,
                                    st.session_state.cache_sub_category,
                                    st.session_state.cache_model_number,
                                )
                            )
                            st.session_state.flag_use_context_cache = False

                        warning_configuring_chatbot.empty()

                if st.session_state.cache_model_number:
                    with sidebar_container:
                        configuration_information = (
                            f"Double-check information before relying on it."
                        )

                        sac.alert(
                            label=f"Our chatbot is still learning! ",
                            description=configuration_information,
                            color="orange",
                            icon=True,
                        )

                    with st.sidebar:
                        st.write(" ")
                        st.markdown("<BR>" * 2, unsafe_allow_html=True)

                        cola, colb = st.columns(
                            [4, 1], vertical_alignment="center")

                        with colb:
                            if st.button(
                                "",
                                icon=":material/cancel:",
                                use_container_width=True,
                                help="Clear and Reconfigure",
                            ):
                                del st.session_state.cache_model_number
                                del st.session_state.cache_brand
                                del st.session_state.cache_category
                                del st.session_state.cache_sub_category

                                del st.session_state.messages
                                del st.session_state.chat
                                del st.session_state.service_guide

                                del st.session_state.gemini_flash
                                del st.session_state.flag_use_context_cache

                                st.rerun()

                        with cola:
                            service_manual_bucket = ServiceManualBucket()
                            service_manual_url = service_manual_bucket.fetch_service_manual_url(
                                f"{
                                    st.session_state.cache_category.lower().replace(
                                        ' ',
                                        '_').replace(
                                        '-',
                                        '_').replace(
                                        '/',
                                        '_')}/{
                                    st.session_state.cache_sub_category.lower().replace(
                                        " ",
                                        "_").replace(
                                        "-",
                                        "_").replace(
                                        "/",
                                        "_")}_service_guide.pdf"
                            )

                            try:
                                st.link_button(
                                    label=f"Launch Service Guide",
                                    url=service_manual_url,
                                    icon=":material/quick_reference:",
                                    use_container_width=True,
                                )

                            except BaseException:
                                st.error("Unable to display button")

                if "chat" not in st.session_state:
                    service_engineer_chatbot = ServiceEngineerChatbot()

                    st.session_state.chat = (
                        service_engineer_chatbot.create_chat_instance(
                            context_cache=st.session_state.gemini_flash,
                            chat_history=st.session_state.messages,
                            use_context_cache=st.session_state.flag_use_context_cache,
                        )
                    )

                    welcome_message = f"""
                    Hello there! I am your virtual assistant, LogIQ.

                    I'm ready to assist you with questions on **{st.session_state.cache_brand} {st.session_state.cache_sub_category}** (Model: {st.session_state.cache_model_number}).  I can help you troubleshoot issues, replace parts, and offer useful maintenance tips to keep your appliance running smoothly.

                    What can I do for you today to make sure your appliance works at its best?
                    """
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": welcome_message,
                        }
                    )
                    st.rerun()

                if prompt := st.chat_input("Type your question here..."):
                    prompt = bleach.clean(prompt)
                    st.session_state.messages.append(
                        {"role": "user", "content": prompt}
                    )

                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        with st.spinner(
                            "Thinking...", show_time=True
                        ):

                            if st.session_state.flag_use_context_cache == True:
                                response_from_model = (
                                    st.session_state.chat.send_message(
                                        message=prompt,
                                    )
                                )

                            else:
                                service_manual_uri = (
                                    "gs://service_manual_bucket/"
                                    + st.session_state.cache_category.lower()
                                    .replace(" ", "_")
                                    .replace("-", "_")
                                    .replace("/", "_")
                                    + "/"
                                    + st.session_state.cache_sub_category.lower()
                                    .replace(" ", "_")
                                    .replace("-", "_")
                                    .replace("/", "_")
                                    + "_service_guide.pdf"
                                )

                                response_from_model = (
                                    st.session_state.chat.send_message(
                                        message=[
                                            types.Part.from_uri(
                                                file_uri=service_manual_uri,
                                                mime_type="application/pdf",
                                            ),
                                            prompt,
                                        ],
                                    )
                                )

                            def response_generator(response):
                                for word in response:
                                    time.sleep(0.025)

                                    try:
                                        yield word.text
                                    except Exception as err:
                                        yield word

                            try:
                                response = st.write_stream(
                                    response_generator(
                                        response_from_model.text)
                                )

                            except Exception as err:
                                fallback_message = (
                                    f"Sorry, I am unable to answer this.\nReason: {err}"
                                )

                                response = st.write_stream(
                                    response_generator(fallback_message)
                                )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

            else:
                with st.sidebar:
                    st.write(" ")
                    st.markdown(
                        "<BR>" * 2,
                        unsafe_allow_html=True,
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

                st.markdown(
                    "<BR><BR><BR><H2>LogIQ - Service Engineer Chatbot</H2><H4>Diagnose, Troubleshoot, and Repair White Label Appliances with Expert Precision!</H4>Facing an issue with your kitchen appliance, but not sure whom to call? Or perhaps you need immediate assistance with a repair? Simply describe your problem, and our chatbot powered by Gemini 1.5 will help you troubleshoot these problems in a single tap!",
                    unsafe_allow_html=True,
                )

                usage_instructions = """
                **Here's how you can get started:**

                1. Simply select the brand and model of your appliance, and type in the issues you're facing or the specific service you need.
                2. Wait for the chatbot to analyze the service manuals/guides and provide expert advice and troubleshooting tips right away.
                """
                st.info(usage_instructions)

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
                "<H2>Welcome to LogIQ!</H2>LogIn to access the Engineer Application. Authorized access by engineers only.",
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
                "LogIn to the Engineer App", use_container_width=True, type="primary"
            )

            if colb.button("", icon=":material/copyright:",
                           help="Attribution", use_container_width=True):
                dialog_attribution()

            if st.session_state.engineer_id is False:
                colx, _ = st.columns([8, 1])

                warning_message = colx.error(
                    "Invalid Username or Password", icon=":material/error:"
                )

                time.sleep(3)
                st.session_state.engineer_id = None

                warning_message.empty()

            if button_login:
                email = email.lower()

                try:
                    api_key = st.secrets["FIREBASE_AUTH_WEB_API_KEY"]
                    base_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

                    if "@" not in email:
                        username = email.upper()
                        user = firebase_admin.auth.get_user(username)
                        email = user.email

                    query_engineers = QueryEngineers()
                    engineer_exists = query_engineers.check_engineer_exists_by_email(
                        email
                    )

                    if engineer_exists:
                        data = {"email": email, "password": password}

                        response = requests.post(
                            base_url.format(api_key=api_key), json=data
                        )

                        if response.status_code == 200:
                            st.toast("Logging you in to the engineer app")
                            data = response.json()

                            st.cache_data.clear()
                            st.cache_resource.clear()

                            st.session_state.engineer_id = (
                                firebase_admin.auth.get_user_by_email(
                                    email).uid
                            )
                            st.rerun()

                        else:
                            st.session_state.engineer_id = False
                            st.rerun()

                    else:
                        st.toast(
                            "No engineer found with this username. Please check the username and try again."
                        )

                        st.session_state.engineer_id = False
                        time.sleep(5)

                        st.rerun()

                except Exception as error:
                    st.session_state.engineer_id = False
                    st.rerun()
