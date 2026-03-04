import json
from typing import Any

data = {
    "restaurants" : [
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Vastra Gotaland",
                "city" : "Gothenburg",
                "street" : "Kungsgatan 1"
            },
            "name" : "Kebab123",
            "seats" : 10,
            "cuisine" : "kebab"
        },
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Vastra Gotaland",
                "city" : "Gothenburg",
                "street" : "Avenyn 10"
            },
            "name" : "Pasta Palace",
            "seats" : 25,
            "cuisine" : "Italian"
        },
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Stockholm",
                "city" : "Stockholm",
                "street" : "Drottninggatan 5"
            },
            "name" : "Sushi Zen",
            "seats" : 15,
            "cuisine" : "Japanese"
        },
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Skane",
                "city" : "Malmo",
                "street" : "Stortorget 2"
            },
            "name" : "The Green Garden",
            "seats" : 40,
            "cuisine" : "Vegetarian"
        },
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Vastra Gotaland",
                "city" : "Gothenburg",
                "street" : "Linnégatan 15"
            },
            "name" : "Burger Joint",
            "seats" : 20,
            "cuisine" : "American"
        },
        {
            "location" : {
                "country" : "Sweden",
                "region" : "Uppsala",
                "city" : "Uppsala",
                "street" : "Svartbäcksgatan 1"
            },
            "name" : "Viking Feast",
            "seats" : 50,
            "cuisine" : "Nordic"

        }
    ]
}

class FakeDB():
    def __init__(self, data: dict[str,list[dict[str,Any]]]):
        self.data = data

    def query(self, table, predicate):
        return [
            row for row in self.data.get(table, [])
            if predicate(row)
        ]



