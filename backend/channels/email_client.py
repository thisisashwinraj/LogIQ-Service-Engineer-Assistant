import streamlit as st

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


class TransactionalEmails:
    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = st.secrets["BREVO_API_KEY"]

        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        self.sender = {
            "email": "rajashwin733@gmail.com",
            "name:": "LogIQ Support"}

    def send_onsite_service_request_confirmation_mail(
        self,
        receiver_full_name,
        receiver_email,
        service_request_id,
    ):
        to = [
            {
                "email": receiver_email,
                "name:": receiver_full_name,
            }
        ]

        subject = "You service request has been cretaed succesfully!"

        html_content = f"""
        <HTML>
            <BODY>
                Dear {receiver_full_name},
                <BR><BR>
                Your request for onsite service has been successfully created with id: <B>{service_request_id}</B>.
                <BR><BR>
                Our team is currently processing your request and will assign a qualified service engineer to your case as soon as possible. You'll receive an update with the engineer's details shortly.
                <BR><BR>
                If you have any questions in the meantime, feel free to contact us.
                <BR><BR>
                Warm regards,
                <BR>
                LogIQ Support Team
            </BODY>
        </HTML>
        """

        smtp_payload = sib_api_v3_sdk.SendSmtpEmail(
            sender=self.sender, to=to, subject=subject, html_content=html_content
        )

        try:
            api_response = self.api_instance.send_transac_email(smtp_payload)
            return True

        except ApiException as e:
            return False

    def send_onsite_service_request_engineer_assigned_mail(
        self,
        receiver_full_name,
        receiver_email,
        service_request_id,
        engineer_id,
        engineer_name,
        engineer_phone,
        engineer_email,
    ):
        to = [
            {
                "email": receiver_email,
                "name:": receiver_full_name,
            }
        ]

        subject = f"Service Request {service_request_id} Assigned to Engineer!"

        html_content = f"""
        <HTML>
            <BODY>
                Dear {receiver_full_name},
                <BR><BR>
                We are pleased to inform you that an engineer has been assigned to your service request, with Request Id: <B>{service_request_id}</B>.
                <BR><BR>
                Below are the details of the assigned engineer:
                <BR><UL>
                    <LI><B>Engineer ID:</B> {engineer_id}</LI>
                    <LI><B>Engineer Name:</B> {engineer_name}</LI>
                    <LI><B>Phone Number:</B> +91-{engineer_phone}</LI>
                    <LI><B>Email Address:</B> {engineer_email}</LI>
                </UL>
                The engineer will contact you shortly to schedule a convenient time for the service. If you have any questions or need further assistance, please feel free to reach out to us.
                <BR><BR>
                Thank you for choosing LogIQ. We appreciate the opportunity to serve you!
                <BR><BR>
                Warm regards,
                <BR>
                LogIQ Support Team
            </BODY>
        </HTML>
        """

        smtp_payload = sib_api_v3_sdk.SendSmtpEmail(
            sender=self.sender, to=to, subject=subject, html_content=html_content
        )

        try:
            api_response = self.api_instance.send_transac_email(smtp_payload)
            return True

        except ApiException as e:
            return False

    def send_onsite_service_request_resolution_started_mail(
        self,
        receiver_full_name,
        receiver_email,
        service_request_id,
        engineer_id,
        engineer_name,
    ):
        to = [
            {
                "email": receiver_email,
                "name:": receiver_full_name,
            }
        ]

        subject = f"Service Resolution Has Begun - Request Id: {service_request_id}!"

        html_content = f"""
        <HTML>
            <BODY>
                Dear {receiver_full_name},
                <BR><BR>
                We are happy to inform you that the assigned engineer, {engineer_name} (Id: {engineer_id}), has been successfully verified and has started working on resolving your service request.
                <BR><BR>
                The resolution process is now underway, and we will keep you updated on the progress. If you have any questions or concerns, please feel free to contact us at customer.support@logiq.com.
                <BR><BR>
                Thank you for your patience and trust in LogIQ. We are committed to providing you with the best service experience.
                <BR><BR>
                Warm regards,
                <BR>
                LogIQ Support Team
            </BODY>
        </HTML>
        """

        smtp_payload = sib_api_v3_sdk.SendSmtpEmail(
            sender=self.sender, to=to, subject=subject, html_content=html_content
        )

        try:
            api_response = self.api_instance.send_transac_email(smtp_payload)
            return True

        except ApiException as e:
            return False

    def send_onsite_service_request_resolved_mail(
        self,
        receiver_full_name,
        receiver_email,
        service_request_id,
        engineer_id,
        engineer_name,
        ticket_activity,
        additional_notes,
    ):
        to = [
            {
                "email": receiver_email,
                "name:": receiver_full_name,
            }
        ]

        subject = f"Your Service Request {service_request_id} Has Been Resolved!"

        html_content = f"""
        <HTML>
            <BODY>
                Dear {receiver_full_name},
                <BR><BR>
                We are pleased to inform you that your service request has been successfully resolved by our engineer, {engineer_name} (Id: {engineer_id}).
                <BR><UL>
                    <LI><B>Engineer Activity:</B><BR>{ticket_activity}</LI><BR>
                    <LI><B>Additional Notes:</B><BR>{additional_notes}</LI>
                </UL>
                We hope everything is now functioning as expected. If you have any further concerns or require additional assistance, please don't hesitate to contact us at customer.support@logiq.com.
                <BR><BR>
                Thank you for choosing LogIQ. We value your trust and look forward to serving you again in the future!
                <BR><BR>
                Warm regards,
                <BR>
                LogIQ Support Team
            </BODY>
        </HTML>
        """

        smtp_payload = sib_api_v3_sdk.SendSmtpEmail(
            sender=self.sender, to=to, subject=subject, html_content=html_content
        )

        try:
            api_response = self.api_instance.send_transac_email(smtp_payload)
            return True

        except ApiException as e:
            return False
