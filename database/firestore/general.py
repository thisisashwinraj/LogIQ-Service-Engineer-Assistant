import bcrypt
import random
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore


class OnsiteServiceRequestCollection:
    def __init__(self):
        try:
            cred = credentials.Certificate(
                "config/firebase_service_account_key.json")
            firebase_admin.initialize_app(cred)
        except BaseException:
            pass

        self.db = firestore.client()

    def _generate_request_id(self):
        request_id = "2" + "".join([str(random.randint(0, 9))
                                   for _ in range(11)])
        return request_id

    def create_onsite_service_request(self, customer_id, service_request_data):
        request_id = self._generate_request_id()
        current_timestamp = datetime.utcnow() + timedelta(hours=5, minutes=30)

        onsite_service_request_data = {
            "address": {
                "city": service_request_data["city"],
                "state": service_request_data["state"],
                "street": service_request_data["street"],
                "zipcode": service_request_data["zipcode"],
            },
            "appliance_details": {
                "category": service_request_data["category"],
                "sub_category": service_request_data["sub_category"],
                "brand": service_request_data["brand"],
                "model_number": service_request_data["model_number"],
                "serial_number": service_request_data["serial_number"],
                "purchased_from": service_request_data["purchased_from"],
                "seller": service_request_data["seller"],
                "purchase_date": service_request_data["purchase_date"],
                "installation_date": service_request_data["installation_date"],
                "warranty_period": service_request_data["warranty_period"],
                "warranty_expiration": service_request_data["warranty_expiration"],
                "appliance_image_url": service_request_data["appliance_image_url"],
            },
            "assigned_to": "",
            "assigned_on": "",
            # unassigned, confirmation_pending, confirmed, rejected, suspended, cancelled
            "assignment_status": "unassigned",
            "created_on": current_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_contact": {
                "phone_number": service_request_data["phone_number"],
                "email": service_request_data["email"],
            },
            "description": service_request_data["description"],
            "service_invoice_url": "",
            "request_title": service_request_data["request_title"],
            "request_type": service_request_data["request_type"],
            "resolution": {
                "action_performed": "",
                "additional_notes": "",
                "end_date": "",
                "feedback": {
                    "comments": "",
                    "rated_on": "",
                    "ratings": "",
                },
                "parts_purchased": "",
                "requested_service": "",
                "start_date": "",
            },
            "ticket_status": "open",  # open, on-hold, resolved
            "total_cost": "",
        }

        self.db.collection("service_requests").document("onsite").collection(
            customer_id
        ).document(request_id).set(onsite_service_request_data)
        return request_id

    def update_engineer_for_service_request(
            self, customer_id, request_id, engineer_id):
        try:
            service_request_ref = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(request_id)
            )

            service_request_ref.update(
                {
                    "assigned_to": engineer_id,
                    "assignment_status": "pending_confirmation",
                }
            )

            return True

        except BaseException:
            return False

    def assign_service_request_to_admin(
        self, customer_id, request_id, assignment_notes
    ):
        try:
            service_request_ref = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(request_id)
            )

            service_request_ref.update(
                {
                    "assigned_to": "ADMIN",
                    "assignment_notes": assignment_notes,
                }
            )

            return True

        except BaseException:
            return False

    def update_title_and_description_for_service_request(
        self,
        customer_id,
        service_request_id,
        updated_request_title,
        updated_description,
    ):
        try:
            service_request_ref = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(service_request_id)
            )

            service_request_ref.update(
                {
                    "request_title": updated_request_title,
                    "description": updated_description,
                }
            )

            return True

        except Exception as error:
            return False

    def update_assignment_status(
            self, customer_id, service_request_id, status):
        try:
            service_request_ref = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(service_request_id)
            )

            service_request_ref.update(
                {
                    "assignment_status": status,
                }
            )

            current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

            service_request_ref.set(
                {"engineer_assigned_on": current_time.strftime(
                    "%Y-%m-%d %H:%M:%S")},
                merge=True,
            )

            return True

        except Exception as error:
            return False

    def fetch_latest_service_request_by_customer_id(
            self, customer_id, limit=2):
        if limit > 0:
            docs = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .order_by("created_on", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
        else:
            docs = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .order_by("created_on", direction=firestore.Query.DESCENDING)
                .stream()
            )

        service_requests = []

        for doc in docs:
            service_requests.append([doc.id, doc.to_dict()])

        return service_requests

    def fetch_all_service_request_by_customer_id(self, customer_id):
        docs = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .order_by("created_on", direction=firestore.Query.DESCENDING)
            .stream()
        )

        service_requests = []

        for doc in docs:
            service_requests.append([doc.id, doc.to_dict()])

        return service_requests

    def fetch_data_for_engineer_assignment(self, customer_id, request_id):
        try:
            doc = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(request_id)
                .get()
            )
        except Exception as error:
            return {}

        request_data = {}

        if doc.exists:
            service_request_data = doc.to_dict()

            request_data["street"] = service_request_data.get(
                "address").get("street")
            request_data["city"] = service_request_data.get(
                "address").get("city")
            request_data["state"] = service_request_data.get(
                "address").get("state")
            request_data["zipcode"] = service_request_data.get(
                "address").get("zipcode")

            request_data["sub_category"] = service_request_data.get(
                "appliance_details"
            ).get("sub_category")
            request_data["request_type"] = service_request_data.get(
                "request_type")

        return request_data

    def fetch_onsite_service_request_by_customer_id(self, customer_id):
        result = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .get()
        )

        if len(result) > 0:
            ticket_ids = []

            for res in result:
                ticket_ids.append(res.id)

            return ticket_ids

        else:
            return None

    def fetch_onsite_service_request_details_by_engineer_id(self, engineer_id):
        docs = self.db.collection("service_requests").document(
            "onsite").collections()

        ticket_ids = {}

        if docs:
            for customer_collection in docs:
                for ticket_doc in customer_collection.where(
                    "assigned_to", "==", engineer_id
                ).stream():
                    service_request_details = ticket_doc.to_dict()

                    service_request_details["customer_id"] = customer_collection.id
                    service_request_details["request_id"] = ticket_doc.id

                    ticket_ids[ticket_doc.get(
                        "created_on")] = service_request_details

            return list(
                dict(sorted(ticket_ids.items(), reverse=True)).values())

        else:
            return []

    def add_service_request_activity(
        self, customer_id, service_request_id, added_by, notes
    ):
        try:
            doc = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(service_request_id)
                .get()
            )

            current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

            new_activity = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "added_by": added_by,
                "notes": notes,
            }

            if doc.exists and "ticket_activity" in doc.to_dict():
                doc.reference.update(
                    {"ticket_activity": firestore.ArrayUnion([new_activity])}
                )

            else:
                doc.reference.set(
                    {"ticket_activity": [new_activity]}, merge=True)

            return True

        except Exception as error:
            return False

    def fetch_service_request_activity(self, customer_id, service_request_id):
        try:
            doc = (
                self.db.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .document(service_request_id)
                .get()
            )

            if doc.exists:
                return doc.to_dict().get("ticket_activity", [])[::-1]

            else:
                return []

        except Exception as error:
            return []

    def generate_engineer_verification_otp(self, customer_id, request_id):
        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

        otp_hash = bcrypt.hashpw(
            otp.encode("utf-8"),
            bcrypt.gensalt(
                rounds=12))

        doc = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
            .get()
        )

        if doc.exists:
            doc.reference.update(
                {"resolution.otp.otp_verify_engineer": otp_hash.decode()}
            )
            return otp

        return None

    def validate_engineer_verification_otp(
            self, customer_id, request_id, input_otp):
        doc = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
            .get()
        )

        if doc.exists:
            try:
                try:
                    otp_hash = (
                        doc.to_dict()
                        .get("resolution")
                        .get("otp")
                        .get("otp_verify_engineer")
                    )

                except Exception as error:
                    return False, 402

                stored_otp = bcrypt.checkpw(
                    input_otp.encode("utf-8"), otp_hash.encode()
                )

                if stored_otp:
                    current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

                    doc.reference.update(
                        {
                            "resolution.start_date": current_time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        }
                    )
                    return True, 200
                else:
                    return False, 401

            except Exception as error:
                return False, 404
        return False, 404

    def fetch_resolution_details_by_appliance_serial_number(
        self, customer_id, serial_number
    ):
        docs = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
        )

        if docs:
            past_resolution_notes = {}

            for ticket_doc in docs.where(
                "appliance_details.serial_number", "==", serial_number
            ).stream():
                service_request_details = ticket_doc.to_dict()
                request_id = ticket_doc.id

                resolution_details = service_request_details.get(
                    "resolution", None)

                if service_request_details.get(
                        "ticket_status").lower() != "resolved":
                    continue

                if resolution_details:
                    if "feedback" in resolution_details:
                        del resolution_details["feedback"]

                    resolution_details["request_title"] = service_request_details.get(
                        "request_title"
                    )
                    resolution_details["description"] = service_request_details.get(
                        "description"
                    )
                    resolution_details["created_on"] = service_request_details.get(
                        "created_on"
                    )

                    past_resolution_notes[request_id] = resolution_details

            return past_resolution_notes

        return None

    def report_unsafe_working_condition(
        self, customer_id, service_request_id, working_condition_description
    ):
        service_request_ref = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(service_request_id)
        )

        if service_request_ref:
            service_request_ref.update(
                {
                    "unsafe_working_condition_reported": working_condition_description,
                }
            )
            return True

        else:
            return False

    def generate_resolution_verification_otp(self, customer_id, request_id):
        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

        otp_hash = bcrypt.hashpw(
            otp.encode("utf-8"),
            bcrypt.gensalt(
                rounds=12))

        doc = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
            .get()
        )

        if doc.exists:
            doc.reference.update(
                {"resolution.otp.otp_verify_resolution": otp_hash.decode()}
            )
            return otp

        return None

    def resolve_service_request(
        self, customer_id, request_id, action_performed, additional_notes, input_otp
    ):
        doc = (
            self.db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
            .get()
        )

        if doc.exists:
            try:
                try:
                    otp_hash = (
                        doc.to_dict()
                        .get("resolution")
                        .get("otp")
                        .get("otp_verify_resolution")
                    )

                except Exception as error:
                    return False, 402

                verify_otp = bcrypt.checkpw(
                    input_otp.encode("utf-8"), otp_hash.encode()
                )

                if verify_otp:
                    current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
                    doc.reference.update(
                        {
                            "resolution.end_date": current_time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "resolution.action_performed": action_performed,
                            "resolution.additional_notes": additional_notes,
                            "ticket_status": "resolved",
                        }
                    )
                    return True, 200

                else:
                    return False, 401

            except Exception as error:
                return False, 404

        return False, 404
