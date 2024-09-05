import urllib3
import json
import os
from collections import defaultdict
from dotenv import load_dotenv
from database import Database
from config import DATABASE

# Searches for .env file 
load_dotenv()
class TellerClient:
    
    BASE_URL = "https://api.teller.io/"
    TELLER_APPLICATION_ID = os.environ.get('TELLER_APPLICATION_ID')
    TELLER_ENVIRONMENT_TYPE = os.environ.get('TELLER_ENVIRONMENT_TYPE')
    TRANSACTION_COUNT = os.environ.get('TRANSACTION_COUNT')
    # python dict to hold lists
    banks = defaultdict(list)
    bank_tokens = []
    transactions = defaultdict(list)
    teller_accounts = defaultdict()

    # Variables to see if certificate and private key are found
    cert_found = None
    key_found = None


    # default constructor
    def __init__(self):
        self.get_tokens()

        certificate = os.environ.get('CERTIFICATE')
        key = os.environ.get('KEY')

        # Checks if Certificate is present
        if certificate and os.path.isfile(certificate):
            self.cert_found = True
        else:
            print("Certificate file not found!")
            self.cert_found = False

        # Checks if Private Key is present
        if key and os.path.isfile(key): 
            self.key_found = True
        else:
            print("Key file not found!")
            self.key_found = False
        
        if self.cert_found and self.key_found:
            self.http = urllib3.PoolManager(
                cert_file = certificate,   
                cert_reqs = "CERT_REQUIRED",
                key_file = key   
            )
        else:
            print("Please pass in your Teller Certificate and Keys")
    
    # Function that gets latest bank tokens 
    def get_tokens(self):
        self.bank_tokens.clear()
        db = Database(DATABASE)
        
        try:
            connections = db.view_tokens()

            self.bank_tokens = [connection[2] for connection in connections]
            self.banks = {token: '' for token in self.bank_tokens} 
        
        finally:
            db.close()

    # function for getting the account ids
    def list_accounts(self):
        for bank_token, accountid in self.banks.items():
            try:
                # resp is the response of a GET for accounts using the bank_token for the header
                resp = self._get(f'/accounts', bank_token)

                # uses json.loads to change format to json
                resp_json = json.loads(resp.data)
                # empty list to add the Account IDs that are associated with certain bank
                acctid = []
                # loops for every account found in the linked bank
                for account in resp_json:
                    acctid.append(account['id'])
                    self.teller_accounts[account['name'] + " " + account['last_four']] = account['id']
                # adds the Account IDs to the current bank
                self.banks[bank_token] = acctid
            except Exception as e:
                print("Teller API Connection Down")

    def list_account_all_transactions(self, account_id, bank_token):
        self.transactions.clear()
        try:
            resp = self._get(f'/accounts/{account_id}/transactions', bank_token)
            resp_json = json.loads(resp.data) 

            if 'error' in resp_json:
                error_message = resp_json['error'].get('message', '')
                error_code = resp_json['error'].get('code', '')

                if error_code == 'enrollment.disconnected.credentials_invalid':
                    print("Credentials are invalid. Please reauthenticate.")
                else:
                    print(f"Error occurred: {error_message} (Code: {error_code})")
                return
            self.transactions[account_id] = resp_json
        except Exception as e:
            print(f"An error occurred: {e}")

    # function for getting the transactions for a given Acccount in a given Bank
    def list_account_auto_transactions(self, account_id, bank_token):
        try:
            resp = self._get(f'/accounts/{account_id}/transactions?count={self.TRANSACTION_COUNT}', bank_token)
            resp_json = json.loads(resp.data)

            if 'error' in resp_json:
                error_message = resp_json['error'].get('message', '')
                error_code = resp_json['error'].get('code', '')

                if error_code == 'enrollment.disconnected.credentials_invalid':
                    print("Credentials are invalid. Please reauthenticate.")
                else:
                    print(f"Error occurred: {error_message} (Code: {error_code})")

                return
            self.transactions[account_id] = resp_json
        except Exception as e:
            print(f"An error occurred: {e}")

    # Generic for GET API that uses the BASE_URL and path, and creates the necessary auth headers using the bank_token passed
    def _get(self, path, bank_token):
        return self.http.request('GET', self.BASE_URL + path, headers = urllib3.make_headers(basic_auth = bank_token + ":"))

    def addToList(self,bank_token):
            self.bank_tokens.append(bank_token)
            for b in self.bank_tokens:      
                self.banks[b] = ''    