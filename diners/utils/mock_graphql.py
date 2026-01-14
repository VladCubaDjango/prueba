class MockResponse:
    def __init__(self, data=None):
        self._data = data or {"data": {}}

    def json(self):
        return self._data


class MockGraphqlService:
    """A small mock GraphQL service that returns safe defaults for local development.
    Methods return objects with a .json() method to mimic requests.Response used in the codebase.
    """

    # sample data used for offline testing
    SAMPLE_DINERS = [
        {"person": {"id": 1, "name": "Alice"}, "paymentMethod": "AP", "diningRoom": {"id": 1, "name": "North Dining"}},
        {"person": {"id": 2, "name": "Bob"}, "paymentMethod": "CA", "diningRoom": {"id": 2, "name": "South Dining"}},
    ]

    SAMPLE_AREAS = [
        {"id": 1, "name": "Area 1", "personSet": [{"id": 1}, {"id": 2}]},
    ]

    def get_token(self):
        return "mock-token"

    def get_diner_api(self, id):
        for d in self.SAMPLE_DINERS:
            if str(d['person']['id']) == str(id):
                return MockResponse({"data": {"dinerById": d}})
        # fallback
        return MockResponse({
            "data": {
                "dinerById": {
                    "person": {"id": id, "name": "Local User", "position": None, "area": {"id": 1, "name": "Local Area"}},
                    "paymentMethod": "AP",
                    "diningRoom": {"id": 1, "name": "Local Dining"},
                    "isDiet": False,
                }
            }
        })

    def get_PM_position_by_idPerson(self, id):
        return MockResponse({"data": {"personById": {"position": None, "dinerRelated": {"paymentMethod": "AP"}, "name": "Local User"}}})

    def get_namePerson_by_idPerson(self, id):
        return MockResponse({"data": {"personById": {"name": "Local User"}}})

    def get_namePerson_and_amount_by_idPerson(self, id):
        return MockResponse({"data": {"personById": {"name": "Local User", "advancepaymentRelated": {"balance": 100}}}})

    def get_idsPersons_of_area_by_idPerson(self, id):
        return MockResponse({"data": {"personById": {"area": {"personSet": self.SAMPLE_AREAS[0]['personSet']}}}})

    def get_diners_by_dinningroom(self, id):
        diners = [d for d in self.SAMPLE_DINERS if d['diningRoom']['id'] == int(id)]
        return MockResponse({"data": {"diningRoomById": {"dinerSet": diners}}})

    def get_diningrooms_api(self):
        return MockResponse({"data": {"allDiningRooms": [{"id": 1, "name": "North Dining"}, {"id": 2, "name": "South Dining"}]}})

    def get_diningroom_persons_api(self, id):
        diners = [d for d in self.SAMPLE_DINERS if d['diningRoom']['id'] == int(id)]
        return MockResponse({"data": {"diningRoomById": {"dinerSet": diners}}})

    def get_idPerson_and_nameArea_by_all_areas_api(self):
        return MockResponse({"data": {"allAreas": self.SAMPLE_AREAS}})

    def get_nameDiningroom_by_idDiningroom_api(self, id):
        rooms = [r for r in self.get_diningrooms_api().json()['data']['allDiningRooms'] if r['id'] == int(id)]
        name = rooms[0]['name'] if rooms else 'Local Dining'
        return MockResponse({"data": {"diningRoomById": {"name": name, "dinerSet": []}}})

    def diners_to_choices(self):
        return [('', '--------------')] + [(d['person']['id'], d['person']['name']) for d in self.SAMPLE_DINERS]

    def create_transaction(self, action, amount, description, person, type, user):
        # return a mock response structure that matches usage in the admin - include resultingBalance
        return MockResponse({"data": {"createTransaction": {"transaction": {"id": 1, "resultingBalance": 100}}}})
