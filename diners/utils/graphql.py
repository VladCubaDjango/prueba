import threading
import time

import requests
from decouple import config
from django.utils.translation import gettext_lazy as _
from requests.exceptions import RequestException

API_TIMEOUT = 20
MARGIN = API_TIMEOUT


class GraphqlService:
    __api_url = config('API_URL')
    __api_username = config('API_AUTH_USER')
    __api_password = config('API_AUTH_PASS')
    __api_token = None
    __created = 0
    __expires = 0
    __refreshExpiresIn = 0
    __refresh_cooldown = 0

    def __init__(self):
        self.__session = requests.Session()
        self.__created, self.__expires, self.__refreshExpiresIn = self.__auth_token()

        auth_token_th = threading.Thread(target=self.__target_auth_token, daemon=True)
        auth_token_th.start()

        refresh_token_th = threading.Thread(target=self.__target_refresh_token, daemon=True)
        refresh_token_th.start()

    def __get_post(self, query, variables=None):
        return self.__session.post(
            self.__api_url,
            json={'query': query, 'variables': variables},
            timeout=API_TIMEOUT,
            verify=False,
        )

    def __get_post_token(self, query, variables=None):
        return self.__session.post(
            self.__api_url,
            json={'query': query, 'variables': variables},
            headers={'Authorization': f'JWT {self.__api_token}'},
            timeout=API_TIMEOUT,
            verify=False,
        )

    def __target_auth_token(self):
        while True:
            time.sleep(self.__refreshExpiresIn - self.__created - MARGIN)
            self.__created, self.__expires, self.__refreshExpiresIn = self.__auth_token()

    def __target_refresh_token(self):
        while True:
            time.sleep(self.__refresh_cooldown - MARGIN)
            self.__created, self.__expires, self.__refreshExpiresIn = self.__refresh_token()

    def __auth_token(self):
        try:
            query = '''
                    mutation auth($username: String!, $password: String!) {
                      tokenAuth(username: $username, password: $password) {
                        payload
                        refreshExpiresIn
                        token
                      }
                    }
                    '''
            variables = {'username': self.__api_username, 'password': self.__api_password}
            resp_json = self.__retrieve_token(query, variables=variables).json()

            if resp_json and 'erros' not in resp_json:
                data = resp_json['data']['tokenAuth']
                payload = data['payload']
                created = payload['origIat']
                expires = payload['exp']
                refreshExpiresIn = data['refreshExpiresIn']
                self.__api_token = data['token']
                self.__refresh_cooldown = expires - created
                return created, expires, refreshExpiresIn
            else:
                created = 0
                expires = MARGIN + 1
                refreshExpiresIn = MARGIN + 1
                self.__refresh_cooldown = expires - created
                self.__api_token = None
                return created, expires, refreshExpiresIn
        except Exception:
            created = 0
            expires = MARGIN + 1
            refreshExpiresIn = MARGIN + 1
            self.__refresh_cooldown = expires - created
            self.__api_token = None
            return created, expires, refreshExpiresIn

    def __refresh_token(self):
        try:
            query = '''
                    mutation refresh($token: String!) {
                      refreshToken(token: $token){
                        payload
                        refreshExpiresIn
                        token
                      }
                    }
                    '''
            variables = {'token': self.__api_token}
            resp_json = self.__retrieve_token(query, variables=variables).json()

            if resp_json and 'erros' not in resp_json:
                data = resp_json['data']['refreshToken']
                payload = data['payload']
                created = payload['origIat']
                expires = payload['exp']
                refreshExpiresIn = data['refreshExpiresIn']
                self.__api_token = data['token']
                return created, expires, refreshExpiresIn
            else:
                return self.__auth_token()
        except Exception:
            return self.__auth_token()

    def __retrieve_token(self, query, variables=None):
        return self.__session.post(
            self.__api_url,
            json={'query': query, 'variables': variables},
            timeout=API_TIMEOUT
        )

    def get_token(self):
        return self.__api_token

    def get_diner_api(self, id):
        query = '''
                query getPerson($id: ID) {
                  dinerById(id: $id) {
                    person {
                      id
                      name
                      area {
                        id
                        name
                      }
                      position
                      advancepaymentRelated {
                        balance
                      }
                    }
                    paymentMethod
                    diningRoom {
                      id
                      name
                    }
                    isDiet
                  }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_nameDiningRoom_by_idPerson_api(self, id):
        query = '''
                query getPerson($id: ID) {
                    dinerById(id: $id) {
                        diningRoom {
                            name
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_personname_areaname(self, id):
        try:
            query = '''
                    query getPerson($id: ID) {
                      personById(id: $id) {
                          name
                          area {
                            name
                          }
                      }
                    }
                    '''
            return self.__get_post(query, {'id': str(id)})
        except RequestException:
            return None

    def get_personname_areaname_dinningroomname(self, id):
        try:
            query = '''
                    query getPerson($id: ID) {
                      personById(id: $id) {
                          name
                          area {
                            name
                          }
                          dinerRelated {
                            diningRoom {
                                name
                            }
                        }
                      }
                    }
                    '''
            return self.__get_post(query, {'id': str(id)})
        except RequestException:
            return None

    def get_personnameby_idPerson(self, id):
        try:
            query = '''
                    query getPerson($id: ID) {
                      personById(id: $id) {
                          name
                      }
                    }
                    '''
            return self.__get_post(query, {'id': str(id)})
        except RequestException:
            return None

    def get_areaName_idPerson(self, id):
        try:
            query = '''
                    query getPerson($id: ID) {
                      personById(id: $id) {
                          area {
                            name
                          }
                      }
                    }
                    '''
            return self.__get_post(query, {'id': str(id)})
        except RequestException:
            return None

    def get_person_api_by_name(self, name):
        query = '''
                query getPersonByName($name: String) {
                    personByName(name: $name){
                        id
                        name
                    }
                }
                '''
        return self.__get_post(query, {'name': name})

    def get_area_api_by_name(self, name):
        query = '''
                query getAreaByName($name: String) {
                    areaByName(name: $name){
                        personSet{
                            id
                        }
                    }
                }
                '''
        return self.__get_post(query, {'name': name})

    def get_area_api(self, id):
        query = '''
                query getArea($id: ID) {
                    areaById(id: $id) {
                        id
                        name
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_diners_api(self):
        query = '{allDiners{person{id,name}}}'
        return self.__get_post(query)

    def get_diners_area_api(self, id):
        query = '''
                query getPersonsArea($id: ID) {
                  areaById(id: $id) {
                    id
                    name
                    personSet{
                      dinerRelated{
                        person{
                          id
                          name
                        }
                        isActive
                        paymentMethod
                      }
                    }
                  }
                }
                '''

        return self.__get_post(query, {'id': str(id)})

    def get_diners_person_api(self, id):
        query = '''
                query getPersonsArea($id: ID) {
                    personById(id: $id) {
                        area {
                            id
                            name
                            personSet {
                                id
                                name
                                dinerRelated {
                                    paymentMethod
                                }
                            }
                        }
                    }
                }
                '''

        return self.__get_post(query, {'id': str(id)})

    def get_active_diners_person_api(self, id):
        query = '''
                query getPersonsArea($id: ID) {
                    personById(id: $id) {
                        area {
                            id
                            name
                            personSet {
                                id
                                name
                                dinerRelated {
                                    paymentMethod
                                }
                                isActive
                            }
                        }
                    }
                }
                '''

        return self.__get_post(query, {'id': str(id)})

    def get_areas_api(self):
        query = '{allAreas{id,name}}'
        return self.__get_post(query)

    def get_allperson_for_allareas(self):
        query = '{allAreas{name,personSet{id}}}'
        return self.__get_post(query)

    def get_diningrooms_api(self):
        query = '{allDiningRooms{id,name}}'
        return self.__get_post(query)

    def get_diningroom_persons_api(self, id):
        query = 'query getDiningRoom($id: ID){diningRoomById(id: $id){name,dinerSet{person{id,name}}}}'
        return self.__get_post(query, {'id': str(id)})

    def create_transaction(self, action, amount, description, person, type, user):
        mutation = '''
                    mutation createTransaction(
                        $action: String!, 
                        $amount: Decimal!, 
                        $description: String!, 
                        $person: ID!, 
                        $type: String!, 
                        $user: String!) {
                        createTransaction(
                            action: $action,
                            amount: $amount,
                            description: $description,
                            person: $person,
                            type: $type,
                            user: $user) {
                                transaction {
                                    id
                                    datetime
                                    type
                                    amount
                                    resultingBalance
                                }
                        }
                    }
                    '''

        variables = {
            'action': action,
            'amount': amount,
            'description': description,
            'person': person,
            'type': type,
            'user': user
        }
        return self.__get_post_token(mutation, variables)

    def diners_to_choices(self):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diners_api()
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    persons = resp_json['data']['allDiners']
                    for element in persons:
                        person = element['person']
                        if person:
                            id = int(person['id'])
                            value = person['name']
                            result.append((id, value))
        except RequestException:
            pass
        return result

    def diners_to_area_choices(self, id):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diners_area_api(id)
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    person_list = resp_json['data']['areaById']['personSet']
                    for element in person_list:
                        dinerRelated = element['dinerRelated']
                        if dinerRelated and dinerRelated['isActive']:
                            person = dinerRelated['person']
                            id = int(person['id'])
                            value = person['name']
                            result.append((id, value))
        except RequestException:
            pass
        return result

    def diners_advanced_to_area_choices(self, id):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diners_area_api(id)
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    person_list = resp_json['data']['areaById']['personSet']
                    for element in person_list:
                        diner = element['dinerRelated']
                        if diner and diner['paymentMethod'] == 'AP':
                            person = diner['person']
                            id = int(person['id'])
                            value = person['name']
                            result.append((id, value))
        except RequestException:
            pass
        return result

    def diners_advanced_to_person_area_choices(self, id):
        result = [
            ('', '--------------')
        ]
        result_area = [
            ('', '--------------')
        ]
        try:
            response = self.get_active_diners_person_api(id)
            if response.ok:
                result = []
                person_list = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    area = resp_json['data']['personById']['area']
                    result_area = [(area['id'], area['name'])]
                    person_list_data = area['personSet'] # AQUI
                    for elem in person_list_data:
                        if elem['isActive']:
                            person_list.append(elem)
                    for element in person_list:
                        diner = element['dinerRelated']
                        if diner and diner['paymentMethod'] == 'AP':
                            id = int(element['id'])
                            value = element['name']
                            result.append((id, value))
        except RequestException:
            pass
        return result, result_area

    def areas_to_choices(self):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_areas_api()
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    person = resp_json['data']['allAreas']
                    for element in person:
                        id = int(element['id'])
                        value = element['name']
                        result.append((id, value))
        except RequestException:
            pass
        return result

    def area_to_choices_by_person(self, id):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diner_api(id)
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    area = resp_json['data']['dinerById']['person']['area']
                    id = int(area['id'])
                    value = area['name']
                    result.append((id, value))
        except RequestException:
            pass
        return result

    def diner_to_choices_by_person(self, id):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diner_api(id)
            if response.ok:
                result = []
                resp_json = response.json()
                if 'errors' not in resp_json:
                    area = resp_json['data']['dinerById']['person']
                    id = int(area['id'])
                    value = area['name']
                    result.append((id, value))
        except RequestException:
            pass
        return result

    def diningrooms_to_choices(self):
        result = [
            ('', '--------------')
        ]
        try:
            response = self.get_diningrooms_api()
            if response.ok:
                resp_json = response.json()
                if 'errors' not in resp_json:
                    result = [('0', _('All'))]
                    person = resp_json['data']['allDiningRooms']
                    for element in person:
                        id = int(element['id'])
                        value = element['name']
                        result.append((id, value))
        except RequestException:
            pass
        return result

    def get_qrcameras_api(self):
        query = '''
                {
                  allQrCamera {
                    id
                    isActive
                    name
                    person {
                      id
                      name
                    }
                    location
                  }
                }
                '''
        return self.__get_post(query)

    def get_PM_position_by_idPerson(self, id):
        query = '''
                query getPerson($id: ID) {
                  personById(id: $id) {
                    name,
                    position,
                    dinerRelated{
                        paymentMethod
                    }
                  }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_PM_by_idPerson(self, id):
        try:
            query = '''
                    query getPerson($id: ID) {
                      personById(id: $id) {
                        dinerRelated{
                            paymentMethod
                        }
                      }
                    }
                    '''
            return self.__get_post(query, {'id': str(id)})
        except RequestException:
            return None

    def get_namePerson_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        name,
                        advancepaymentRelated{
                        balance
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_idsPersons_and_area_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        area {
                            personSet {
                                id,
                                name,
                                expirationDate,
                                area{
                                    name
                                }
                                dinerRelated{
                                    diningRoom{
                                        name
                                    }
                                    isDiet
                                    paymentMethod
                                }
                                advancepaymentRelated{
                                    balance
                                }
                                ,isActive
                            }
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_namePerson_and_amount_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        name,
                        position,
                        dinerRelated{
                          paymentMethod
                        }
                        advancepaymentRelated {
                          balance
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_amount_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        advancepaymentRelated {
                          balance
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_idsPersons_of_area_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        area {
                            personSet {
                                id
                            }
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_idTransactions_and_idPerson_of_allTransactions_api(self):
        query = '{allTransactions{id,person{id}}}'
        return self.__get_post_token(query)

    def get_id_and_name_and_nameArea_of_allPersons_api(self):
        query = '{allPerson{id,name,area{name}}}'
        return self.__get_post(query)

    def get_id_and_name_and_nameArea_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                         id,name,expirationDate,area{name},
                              dinerRelated{diningRoom{name},isDiet,paymentMethod}
                              advancepaymentRelated{balance}
                              ,isActive

                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_allDataPerson_by_idPerson(self, id):
        query = '''
                query getPersonById($id: ID) {
                    personById(id: $id){
                        id,
                        name,
                        area{
                            name
                        }
                        advancepaymentRelated{
                            balance
                        }
                        dinerRelated{
                            diningRoom{
                                name
                            }
                            isDiet,
                            paymentMethod
                        }
                        
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_diners_data_api(self):
        query = '''{allDiners{person{id,name,expirationDate,area{name},
                              dinerRelated{diningRoom{name},isDiet,paymentMethod}
                              advancepaymentRelated{balance},isActive
                                                    }}}
                '''
        return self.__get_post(query)

    def get_cameras(self):
        query = '''{
                    allQrCamera{
                        id,
                        name
                        }
                    }
                '''
        return self.__get_post_token(query)

    def get_idPerson_and_nameArea_by_all_areas_api(self):
        query = '{allAreas{name,personSet{id}}}'
        return self.__get_post(query)

    def get_diners_by_dinningroom(self, id):
        query = '''
                query getDiningRoom($id: ID){
                    diningRoomById(id: $id){
                        dinerSet {
                            person {
                                id
                            }
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_datasPersons_by_idDiningrooms_api(self, id):
        query = '''
                query getDiningRoom($id: ID){
                    diningRoomById(id: $id){
                        dinerSet{
                            person{
                                id,
                                name,
                                area{
                                    name
                                }
                            }
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_nameDiningroom_by_idDiningroom_api(self, id):
        query = '''
                query getDiningRoom($id: ID){
                    diningRoomById(id: $id){
                        name,
                        dinerSet {
                            person {
                                id
                            }
                        }
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_nameDiningroom_by_idDiningroom_api_honly(self, id):
        query = '''
                query getDiningRoom($id: ID){
                    diningRoomById(id: $id){
                        name
                    }
                }
                '''
        return self.__get_post(query, {'id': str(id)})

    def get_dataTransaction_by_idTransactions_api(self, id):
        query = '''
                query getTransactions($id: ID){
                    transactionById(id: $id){
                        id,
                        datetime,
                        type,
                        amount
                    }
                }
                '''
        return self.__get_post_token(query, {'id': str(id)})

    def get_dataTransactions_by_idPerson_api(self, id):
        query = '''
                query getTransactions($id: ID){
                    personById(id: $id){
                        name,
                        transactionSet{
                            id,
                            datetime,
                            type,
                            amount
                         }
                     }
                }
                '''
        return self.__get_post_token(query, {'id': str(id)})

    def get_transaction_id_all(self, id):
        query = '''
                query getTransactions($id: ID){
                    transactionById(id: $id){
                        type
                        datetime
                        amount
                        user
                        person{name}
                        folio
                        description
                        previousBalance
                        resultingBalance
                    }
                }'''
        return self.__get_post_token(query, {'id': str(id)})

    def get_idTransactions_by_idPerson(self, id):
        query = '''
                query getPerson($id: ID){
                            personById(id: $id){  name   transactionSet{id}      }}
                '''
        return self.__get_post_token(query, {'id': str(id)})

    def get_all_Person_position_api(self):
        query = '{allPerson{id,name,position}}'
        return self.__get_post(query)

    def invites_id_to_list(self):
        result = []
        response = self.get_all_Person_position_api()
        if response.ok:
            resp_json = response.json()
            if 'errors' not in resp_json:
                person = resp_json['data']['allPerson']
                for element in person:
                    if element['position'] == 'Invitado':
                        result.append(int(element['id']))
        return result

    def get_general(self, query, variables, token):
        if token:
            return self.__get_post_token(query, variables)
        else:
            return self.__get_post(query, variables)
