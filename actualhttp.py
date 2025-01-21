import urllib3
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
class ActualHTTPClient:
    try:
        BASE_URL = os.environ.get('ACTUAL_SERVER_API')
        ACTUAL_BUDGET_SYNC_ID = os.environ.get('ACTUAL_BUDGET_SYNC_ID')
        ACTUAL_API_KEY = os.environ.get('ACTUAL_API_KEY')
    except Exception as e:
        BASE_URL = ''
        ACTUAL_BUDGET_SYNC_ID = ''
        ACTUAL_API_KEY = ''
    actual_accounts = defaultdict()

    def __init__(self):
        self.http = urllib3.PoolManager()
        self.list_accounts()

    def list_accounts(self):
        try:
            self.actual_accounts.clear()
            resp = self._get(f'/budgets/{self.ACTUAL_BUDGET_SYNC_ID}/accounts')
            respJson = json.loads(resp.data)
            for data, accounts in respJson.items():
                for account in accounts:
                    self.actual_accounts[account['id']] = account['name']
        except Exception as e:
            print(f'Actual Budget API Error Found: {e}')

    def create_accounts(self, encoded_body):        
        resp = self._post(f'/budgets/{self.ACTUAL_BUDGET_SYNC_ID}/accounts', encoded_body)

    def import_transactions(self, account, encoded_body):
        resp = self._post(f'/budgets/{self.ACTUAL_BUDGET_SYNC_ID}/accounts/{account}/transactions/import', encoded_body)

    def _get(self, path):
        return self.http.request('GET', self.BASE_URL + path, headers = {"x-api-key" : self.ACTUAL_API_KEY})

    def _post(self, path, encoded_body):
        # print("Now requesting...")
        response = self.http.request('POST', self.BASE_URL + path, 
            headers = { 
                        "x-api-key" : self.ACTUAL_API_KEY, 
                        'accept' : 'application/json', 
                        'Content-Type' : 'application/json'
                    }, 
            body = encoded_body
        )
        while not response.isclosed():
            print("Waiting for response to complete")
        # print("Complete!")
        return response