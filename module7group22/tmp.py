import copy
import inspect
from rapidfuzz import process, fuzz
import json
from fakedb import FakeDB, data  # Import FakeDB and data
from typing import Any, Callable
from datetime import date


class Frame:
    def __init__(
        self,
        parent=None,
    ):
        self.name = type(self).__name__
        self.completed = False
        self.parent = parent
        method_members = inspect.getmembers(self, predicate=inspect.ismethod)
        var_members = vars(self).items()
        self.actions = {
            name.removeprefix("action_"): method
            for name, method in method_members
            if name.startswith("action_")
        }
        self.fields: dict[str, Any] = {
            name.removeprefix("field_"): field
            for name, field in var_members
            if name.startswith("field_")
            and not name.startswith(("field_prompt_", "field_expected_answer_"))
        }
        self.field_prompts: dict[str, str] = {
            name.removeprefix("field_prompt_"): field
            for name, field in var_members
            if name.startswith("field_prompt_")
        }
        self.field_expected_answers: dict[str, list[str]] = {
            name.removeprefix("field_expected_answer_"): field
            for name, field in var_members
            if name.startswith("field_expected_answer_")
        }
        self.action_tokens = {
            action: {k: None for k in inspect.signature(fn).parameters.keys()}
            for action, fn in self.actions.items()
        }

    def check_completed(self):
        for _, value in self.fields.items():
            if value is None:
                return False
            if isinstance(value, Frame) and not value.completed:
                return False
        self.completed = True
        return True

    def get_field_expected_answers_flattened(self):
        return {
            answer: field
            for field, answers in self.field_expected_answers.items()
            for answer in answers
        }

    def get_field_prompt(self, field: str):
        return self.field_prompts[field]

    def get_field_expected_answer(self, field: str):
        return self.field_expected_answers[field]


# Initialize the database globally for use by Location frames
db = FakeDB(data)


# Implementations
class Date(Frame):
    def __init__(self, year=None, month=None, day=None, parent=None):
        self.year = year
        self.month = month
        self.day = day
        self.expected_answer = ["ON THE _"]
        self.field_year = year
        self.field_month = month
        self.field_day = day
        self.field_prompt_year = "WHAT YEAR?"
        self.field_prompt_month = "WHAT MONTH?"
        self.field_prompt_day = "WHAT DAY?"
        self.field_expected_answer_year_add = ["THE YEAR IS _"]
        self.field_expected_answer_month_add = ["THE MONTH IS _"]
        self.field_expected_answer_day_add = ["ON THE _", "THE DAY IS _"]
        super().__init__(
            parent=parent,
        )

    def action_year_add(self, year):
        self.field_year = year
        self.check_completed()
        return self

    def action_month_add(self, month):
        self.field_month = month
        self.check_completed()
        return self

    def day_add(self, day):
        self.day = day
        self.check_completed()
        return self


class Duration(Frame):
    def __init__(self, time=None, parent=None):
        self.time = time
        self.expected_answer = ["I WANT TO STAY FOR _ _", "I WANT TO SPEND _ _ OF TIME"]
        self.field_time = time
        self.field_prompt_time = "HOW LONG DO YOU WANT TO STAY?"
        self.field_expected_answer_time_add = [
            "I WANT TO STAY FOR _ _",
            "I WANT TO SPEND _ _ OF TIME",
        ]
        super().__init__(parent=parent)

    def action_time_add(self, time):
        self.field_time = time
        self.check_completed()
        return self


class Location(Frame):
    def __init__(
        self, country=None, city=None, street=None, parent=None, query_type="restaurants"
    ):
        self.db = db
        self.query_type = query_type
        self.field_country = country
        self.field_city = city
        self.field_street = street
        self.field_prompt_country = "WHICH COUNTRY?\n" + self.country_suggest()
        self.field_prompt_city = "WHICH CITY?\n" + self.city_suggest()
        self.field_prompt_street = "WHICH STREET?\n" + self.street_suggest()
        self.field_expected_answer_country_add = ["THE COUNTRY IS _", "COUNTRY NAME IS _"]
        self.field_expected_answer_city_add = ["THE CITY IS _", "CITY NAME IS _"]
        self.field_expected_answer_street_add = ["STREET NAME IS _", "THE STREET IS _"]
        super().__init__(parent=parent)

    def country_suggest(self) -> str:
        results = self.db.query(
            self.query_type,
            lambda r: (
                self.field_city is None
                or r["location"]["city"].lower() == self.field_city.lower()
            )
            and (
                self.field_street is None
                or r["location"]["street"].lower() == self.field_street.lower()
            ),
        )
        options = sorted({r["location"]["country"] for r in results})
        return f"(options: {', '.join(options)})" if options else ""

    def city_suggest(self) -> str:
        results = self.db.query(
            self.query_type,
            lambda r: (
                self.field_country is None
                or r["location"]["country"].lower() == self.field_country.lower()
            )
            and (
                self.field_street is None
                or r["location"]["street"].lower() == self.field_street.lower()
            ),
        )
        options = sorted({r["location"]["city"] for r in results})
        return f"(options: {', '.join(options)})" if options else ""

    def street_suggest(self) -> str:
        results = self.db.query(
            self.query_type,
            lambda r: (
                self.field_country is None
                or r["location"]["country"].lower() == self.field_country.lower()
            )
            and (
                self.field_city is None
                or r["location"]["city"].lower() == self.field_city.lower()
            ),
        )
        options = sorted({r["location"]["street"] for r in results})
        return f"(options: {', '.join(options)})" if options else ""

    def action_country_add(self, country):
        self.field_country = country
        self.field_prompt_city = "WHICH CITY?\n" + self.city_suggest()
        self.field_prompt_street = "WHICH STREET?\n" + self.street_suggest()
        self.check_completed()
        return self

    def action_city_add(self, city):
        self.field_city = city
        self.field_prompt_country = "WHICH COUNTRY?\n" + self.country_suggest()
        self.field_prompt_street = "WHICH STREET?\n" + self.street_suggest()
        self.check_completed()
        return self

    def action_street_add(self, street):
        self.field_street = street
        self.field_prompt_country = "WHICH COUNTRY?\n" + self.country_suggest()
        self.field_prompt_city = "WHICH CITY?\n" + self.city_suggest()
        self.check_completed()
        return self


class RestaurantVisit(Frame):
    def __init__(self, location=None, date=None, parent=None, name=None):
        self.location = location
        self.date = date
        self.name = name
        self.field_location = location
        self.field_date = date
        self.field_name = name
        self.field_prompt_location = "WHERE IS THE RESTAURANT LOCATED?"
        self.field_prompt_date = "WHEN DO YOU WANT TO GO TO THE RESTAURANT?"
        self.field_prompt_name = "WHAT IS THE NAME OF THE RESTAURANT?"
        self.field_expected_answer_location_add_country = [
            "ITS IN THE COUNTRY OF _",
            "THE COUNTRY IS _",
        ]
        self.field_expected_answer_location_add_city = [
            "ITS IN THE CITY OF _",
            "THE CITY IS _",
        ]
        self.field_expected_answer_location_add_street = [
            "ITS ON _ STREET",
            "THE STREET IS _",
        ]
        self.field_expected_answer_date_add_year = ["I WANT TO GO YEAR _"]
        self.field_expected_answer_date_add_month = [
            "I WANT TO GO THERE IN _",
            "I WANT TO GO THERE THIS _",
        ]
        self.field_expected_answer_date_add_day = ["I WANT TO GO THERE ON THE _"]
        self.field_expected_answer_date_add_nearby_weekday = [
            "THIS MONDAY",
            "THIS TUESDAY",
            "THIS WEDNESDAY",
            "THIS THURSDAY",
            "THIS FRIDAY",
            "THIS SATURDAY",
            "THIS SUNDAY",
        ]
        self.field_expected_answer_name_add = ["IT IS CALLED _ ", "NAME IS _ "]
        super().__init__(parent=parent)

    def action_location_add_country(self, country, parent):
        self.field_location = Location(
            country=country, parent=parent, query_type="restaurants"
        )
        self.check_completed()
        return self.field_location

    def action_location_add_city(self, city, parent):
        self.field_location = Location(city=city, parent=parent, query_type="restaurants")
        self.check_completed()
        return self.field_location

    def action_location_add_street(self, street, parent):
        self.field_location = Location(
            street=street, parent=parent, query_type="restaurants"
        )
        self.check_completed()
        return self.field_location

    def action_date_add_year(self, year, parent):
        self.field_date = Date(year=year, parent=parent)
        self.check_completed()
        return self.field_date

    def action_date_add_month(self, month, parent):
        self.field_date = Date(month=month, parent=parent)
        self.check_completed()
        return self.field_date

    def action_date_add_day(self, day, parent):
        self.field_date = Date(day=day, parent=parent)
        self.check_completed()
        return self.field_date

    def action_date_add_nearby_weekday(self, week_day):
        raise NotImplementedError()

    def action_name_add(self, name):
        self.field_name = name
        self.check_completed()
        return self


class WeatherForecast(Frame):
    def __init__(
        self,
        location=None,
        temperature=None,
        humidity=None,
        weather_type=None,
        parent=None,
    ):
        self.expected_answer = ["WHAT IS THE WEATHER IN _"]
        self.field_location = location
        self.field_temperature = temperature
        self.field_humidity = humidity
        self.field_weather_type = weather_type

        self.field_prompt_location = "WHERE DO YOU WANT THE WEATHER FORECAST FOR?"
        self.field_prompt_temperature = "WHAT TEMPERATURE ARE YOU INTERESTED IN?"
        self.field_prompt_humidity = "WHAT HUMIDITY LEVEL ARE YOU INTERESTED IN?"
        self.field_prompt_weather_type = "WHAT TYPE OF WEATHER ARE YOU LOOKING FOR?"

        self.field_expected_answer_location_add_country = [
            "FOR THE COUNTRY OF _",
            "COUNTRY IS _",
        ]
        self.field_expected_answer_location_add_city = ["FOR THE CITY OF _", "CITY IS _"]
        self.field_expected_answer_location_add_street = [
            "FOR THE STREET _",
            "STREET IS _",
        ]
        self.field_expected_answer_temperature_add = [
            "TEMPERATURE IS _",
            "IT IS _ DEGREES",
        ]
        self.field_expected_answer_humidity_add = [
            "HUMIDITY IS _",
            "IT IS _ PERCENT HUMID",
        ]
        self.field_expected_answer_weather_type_add = ["WEATHER IS _", "IT IS _"]
        super().__init__(parent=parent)

    def action_location_add_country(self, country, parent):
        self.field_location = Location(
            country=country, parent=parent, query_type="weather"
        )
        self.check_completed()
        return self.field_location

    def action_location_add_city(self, city, parent):
        self.field_location = Location(city=city, parent=parent, query_type="weather")
        self.check_completed()
        return self.field_location

    def action_location_add_street(self, street, parent):
        self.field_location = Location(street=street, parent=parent, query_type="weather")
        self.check_completed()
        return self.field_location

    def action_temperature_add(self, temperature):
        self.field_temperature = temperature
        self.check_completed()
        return self

    def action_humidity_add(self, humidity):
        self.field_humidity = humidity
        self.check_completed()
        return self

    def action_weather_type_add(self, weather_type):
        self.field_weather_type = weather_type
        self.check_completed()
        return self


class PublicTransportTrip(Frame):
    def __init__(
        self,
        transport_type=None,
        departure_location=None,
        arrival_location=None,
        parent=None,
    ):
        self.expected_answer = ["I WANT TO TRAVEL BY _"]
        self.field_transport_type = transport_type
        self.field_departure_location = departure_location
        self.field_arrival_location = arrival_location

        self.field_prompt_transport_type = "WHAT TYPE OF TRANSPORT?"
        self.field_prompt_departure_location = "WHERE ARE YOU DEPARTING FROM?"
        self.field_prompt_arrival_location = "WHERE ARE YOU ARRIVING TO?"

        self.field_expected_answer_transport_type_add = ["I WANT TO TRAVEL BY _"]
        self.field_expected_answer_departure_location_add = ["FROM _"]
        self.field_expected_answer_arrival_location_add = ["TO _"]
        super().__init__(parent=parent)

    def action_transport_type_add(self, transport_type):
        self.field_transport_type = transport_type
        self.check_completed()
        return self

    def action_departure_location_add(self, location):
        self.field_departure_location = location
        self.check_completed()
        return self

    def action_arrival_location_add(self, location):
        self.field_arrival_location = location
        self.check_completed()
        return self


class Dialog(Frame):
    def __init__(self):
        self.field_restaurant_visit = None
        self.field_weather_forecast = None
        self.field_public_transport_trip = None

        self.field_prompt_restaurant_visit = None
        self.field_prompt_weather_forecast = None
        self.field_prompt_public_transport_trip = None

        self.field_expected_answer_restaurant_visit_add = ["I WANT TO BOOK A RESTAURANT"]
        self.field_expected_answer_weather_forecast_add = ["WHAT IS THE WEATHER?"]
        self.field_expected_answer_public_transport_trip_add = ["I WANT TO TRAVEL BY BUS"]
        super().__init__(parent=None)

    def action_restaurant_visit_add(self, location, date, parent):
        self.field_restaurant_visit = RestaurantVisit(location, date, parent)
        self.check_completed()
        return self.field_restaurant_visit

    def action_weather_forecast_add(
        self, location, temperature, humidity, weather_type, parent
    ):
        self.field_weather_forecast = WeatherForecast(
            location, temperature, humidity, weather_type, parent
        )
        self.check_completed()
        return self.field_weather_forecast

    def action_public_transport_trip_add(
        self, transport_type, departure_location, arrival_location, parent
    ):
        self.field_public_transport_trip = PublicTransportTrip(
            transport_type, departure_location, arrival_location, parent
        )
        self.check_completed()
        return self.field_public_transport_trip


print(Dialog().fields.keys())
