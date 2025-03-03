import requests
import streamlit as st
import functions_framework

from backend.module.engineer_assignment import OnsiteServiceRequestAssignment


@functions_framework.http
def assign_onsite_service_engineer(request):
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and "customer_id" in request_json:
        customer_id = request_json.get("customer_id")
        request_id = request_json.get("request_id")

        assignment = OnsiteServiceRequestAssignment()
        engineer_id = assignment.assign_available_engineer(
            customer_id,
            request_id,
        )

        if engineer_id:
            return engineer_id
        else:
            return False

    elif request_args and "customer_id" in request_args:
        customer_id = request_args.get("customer_id")
        request_id = request_args.get("request_id")

        assignment = OnsiteServiceRequestAssignment()
        engineer_id = assignment.assign_available_engineer(
            customer_id,
            request_id,
        )

        if engineer_id:
            return engineer_id
        else:
            return False

    else:
        return False


if __name__ == "__main__":
    url = st.secrets["URL_CLOUD_RUN_ONSITE_ENGINEER_ASSIGNMENT_SERVICE"]

    input_customer_id = str(input("Enter customer id: "))
    input_request_id = str(input("Enter request id: "))

    data = {
        "customer_id": input_customer_id,
        "request_id": input_request_id,
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        print("Response:", response.text)

    else:
        print("Failed to create service request:",
              response.status_code, response.text)
