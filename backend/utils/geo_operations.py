import folium
import polyline
import googlemaps

import requests
import streamlit as st


class LocationServices:
    def __init__(self):
        self.gmaps = googlemaps.Client(
            key=st.secrets["GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY"]
        )

    def _get_route_data(self, origin, destination):
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={
            str(
                st.secrets['GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY'])}"

        response = requests.get(url)
        return response.json()

    def display_route_with_folium(self, origin, destination):
        route_data = self._get_route_data(origin, destination)
        route_coordinates = []

        if route_data["status"] == "OK":
            map_polyline = route_data["routes"][0]["overview_polyline"]["points"]
            route_coordinates = polyline.decode(map_polyline)

        folium_map = folium.Map(
            location=route_coordinates[int(len(route_coordinates) / 2)],
            tiles=f"https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}&key={
                str(
                    st.secrets['GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY'])}",
            attr='<a href="https://www.google.com/maps/">Google</a>',
            zoom_start=13,
        )

        folium.PolyLine(route_coordinates, color="#4285F4", weight=5, opacity=1).add_to(
            folium_map
        )

        folium_map.fit_bounds([route_coordinates[0], route_coordinates[-1]])

        return folium_map

    def get_city_and_state_from_zipcode(self, zipcode):
        url = f"https://api.opencagedata.com/geocode/v1/json?q={zipcode}&key={
            st.secrets['OPENCAGE_GEOCODING_API_KEY']}"

        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            if data["results"]:
                result = data["results"][0]

                try:
                    city = result["components"]["state_district"]
                except BaseException:
                    city = None

                try:
                    state = result["components"]["state"]
                except BaseException:
                    state = None

                return city, state

        else:
            return None, None

    def validate_address(self, address):
        result = self.gmaps.addressvalidation(address)
        # GRANULARITY_UNSPECIFIED, SUB_PREMISE, PREMISE, PREMISE_PROXIMITY, BLOCK, ROUTE

        if "result" in result and "verdict" in result["result"]:
            if result["result"]["verdict"]["validationGranularity"] != "OTHER":
                return True

        return False

    def fetch_nearby_districts(self, district_name):
        geocode_result = self.gmaps.geocode(district_name)

        location = geocode_result[0]["geometry"]["location"]

        latitude = location["lat"]
        longitude = location["lng"]

        nearby_result = self.gmaps.places_nearby(
            location=(latitude, longitude),
            radius=50000,
            type="locality",
        )

        nearby_districts = []

        for place in nearby_result["results"]:
            reverse_geocode_result = self.gmaps.reverse_geocode(
                (
                    place["geometry"]["location"]["lat"],
                    place["geometry"]["location"]["lng"],
                )
            )

            for component in reverse_geocode_result[0]["address_components"]:
                if "administrative_area_level_3" in component["types"]:
                    nearby_districts.append(component["long_name"])

        return list(set(nearby_districts))

    def get_batch_travel_distance_and_time_for_engineers(
            self, origins, destination):
        result = self.gmaps.distance_matrix(origins, [destination])

        distances = []

        for element in result["rows"]:
            if element["elements"][0]["status"] == "OK":
                distances.append(
                    element["elements"][0]["distance"]["value"] / 1000)
            else:
                distances.append(float("inf"))

        return distances

    def get_travel_distance_and_time(self, origin, destination):
        distance_matrix = self.gmaps.distance_matrix(
            origins=origin,
            destinations=destination,
            mode="driving",
        )

        if distance_matrix["status"] == "OK":
            element = distance_matrix["rows"][0]["elements"][0]

            if element["status"] == "OK":
                distance = round(element["distance"]["value"] / 1000, 1)
                duration = round(element["duration"]["value"] / 60, 1)

                return distance, duration

            elif element["status"] == "NOT_FOUND":
                return False, "NOT_FOUND"

            else:
                return False, "ZERO_RESULTS"

        else:
            return False, element["status"]
