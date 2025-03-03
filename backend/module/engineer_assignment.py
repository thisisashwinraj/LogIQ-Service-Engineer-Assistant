import html
import time

from backend.utils.geo_operations import LocationServices

from database.cloud_sql.shared import Engineers
from database.firestore.general import OnsiteServiceRequestCollection


class OnsiteServiceRequestAssignment:
    def __init__(self):
        pass

    def _sanitize_request_description(self, description):
        sanitized_description = html.escape(description)
        return sanitized_description

    def _fetch_nearby_available_engineers(
        self, district, appliance_sub_category, service_type
    ):
        engineers = Engineers()
        location_services = LocationServices()

        available_engineer_ids = engineers.fetch_available_engineer_for_service_request(
            district, appliance_sub_category, service_type
        )

        if len(available_engineer_ids) == 0:
            nearby_districts = location_services.fetch_nearby_districts(
                district)

            for nearby_district in nearby_districts:
                nearby_engineers = (
                    engineers.fetch_available_engineer_for_service_request(
                        nearby_district, appliance_sub_category, service_type
                    )
                )

                available_engineer_ids += nearby_engineers

        return available_engineer_ids

    def _rank_engineers(self, customer_address, available_engineer_ids):
        if len(available_engineer_ids) == 0:
            return "ENGINEERS_UNAVAILABLE"

        best_engineer_id = None
        best_engineer_score = float("-inf")

        WEIGHT_PROXIMITY = 0.5
        WEIGHT_RATING = 0.3
        WEIGHT_FAIRNESS = 0.2

        MAX_DISTANCE = 50
        MAX_ACTIVE_TICKETS = 15

        engineer_addresses = []
        engineer_data_map = {}

        engineers = Engineers()

        for engineer_id in available_engineer_ids:
            engineer_data = engineers.fetch_engineer_by_id(
                engineer_id,
                [
                    "street",
                    "city",
                    "district",
                    "state",
                    "zip_code",
                    "rating",
                    "active_tickets",
                ],
            )

            engineer_address = f"{
                engineer_data['street']}, {
                engineer_data['city']}, {
                engineer_data['district']}, {
                engineer_data['state']} - {
                    engineer_data['zip_code']}"

            engineer_addresses.append(engineer_address)
            engineer_data_map[engineer_id] = engineer_data

        location_services = LocationServices()

        try:
            for attempt in range(3):
                distances_to_customer = (
                    location_services.get_batch_travel_distance_and_time_for_engineers(
                        engineer_addresses, customer_address
                    )
                )
                break

        except Exception as error:
            if attempt > 2:
                return "SYSTEM_FAILURE_ROLLBACK"

            time.sleep(5)

        for idx, engineer_id in enumerate(available_engineer_ids):
            engineer_data = engineer_data_map[engineer_id]

            distance_to_customer = distances_to_customer[idx]

            proximity_score = max(0, 1 - (distance_to_customer / MAX_DISTANCE))

            ratings_score = engineer_data["rating"] / 5.0

            fairness_score = max(
                0, 1 - (engineer_data["active_tickets"] / MAX_ACTIVE_TICKETS)
            )

            engineer_score = (
                (proximity_score * WEIGHT_PROXIMITY)
                + (ratings_score * WEIGHT_RATING)
                + (fairness_score * WEIGHT_FAIRNESS)
            )

            if engineer_score > best_engineer_score:
                best_engineer_id = engineer_id
                best_engineer_score = engineer_score

        return best_engineer_id

    def assign_available_engineer(self, customer_id, request_id):
        onsite_service_request_collection = OnsiteServiceRequestCollection()

        appliance_data = (
            onsite_service_request_collection.fetch_data_for_engineer_assignment(
                customer_id,
                request_id,
            )
        )

        customer_address = f"""
            {appliance_data.get('street')},
            {appliance_data.get('city')},
            {appliance_data.get('state')} -
            {appliance_data.get('zipcode')}
        """

        try:
            available_engineer_ids = self._fetch_nearby_available_engineers(
                appliance_data.get("city"),
                appliance_data.get("sub_category"),
                appliance_data.get("request_type"),
            )

            best_matched_engineer_id = self._rank_engineers(
                customer_address, available_engineer_ids
            )

        except Exception as error:
            best_matched_engineer_id = "SYSTEM_FAILURE_ROLLBACK"

        if (best_matched_engineer_id == "ENGINEERS_UNAVAILABLE") or (
            best_matched_engineer_id == "SYSTEM_FAILURE_ROLLBACK"
        ):
            onsite_service_request_collection.assign_service_request_to_admin(
                customer_id, request_id, best_matched_engineer_id
            )

        else:
            onsite_service_request_collection.update_engineer_for_service_request(
                customer_id, request_id, best_matched_engineer_id
            )

        return best_matched_engineer_id
