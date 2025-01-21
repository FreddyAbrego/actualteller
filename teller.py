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
    teller_accounts = defaultdict(list)

    # Variables to see if certificate and private key are found
    cert_found = None
    key_found = None

    # default constructor
    def __init__(self):
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

        self.get_tokens()
        self.list_accounts()
    
    # Function that gets latest bank tokens 
    def get_tokens(self):
        db = Database(DATABASE)
        linked = db.get_all_linked_accounts()
        try:
            connections = db.view_tokens()
            self.bank_tokens = [connection[2] for connection in connections]
            self.banks = {token: '' for token in self.bank_tokens}         
        finally:
            db.close()

    def retrieve_accounts(self, token):
        db = Database(DATABASE)
        # Define a helper function to retrieve and insert accounts
        def fetch_and_insert_accounts(bank_token):
            try:
                resp = self._get(f'/accounts', bank_token)
                resp_json = json.loads(resp.data)

                for account in resp_json:
                    account_name = f"{account['name']} {account['last_four']}"
                    db.insert_account(bank_token, account['id'], account_name, account['type'], account['enrollment_id'])

            except Exception as e:
                print(f"API Connection Down: {str(e)}")

        # If token is "none", use all bank tokens
        if token == "none":
            for bank_token in self.bank_tokens:
                fetch_and_insert_accounts(bank_token)
        else:
            # Otherwise, use the single provided token
            fetch_and_insert_accounts(token)

        print("Teller accounts retrieved.")

    # function for getting the account ids
    def list_accounts(self):
        db = Database(DATABASE)
        if (db.check_token_accounts() == 0):
            print("Teller accounts not found in database, retrieving accounts now.")
            self.retrieve_accounts("none")

        token_accounts = db.get_all_token_accounts()
        for token, account, name_last_four, account_type, enrollment_id in token_accounts:
            if not isinstance(self.banks[token], list):
                self.banks[token] = []
            self.teller_accounts[name_last_four] = [account, account_type, enrollment_id]

            self.banks[token].append(account)
        db.close()

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

    def delete_account(self, account_id, bank_token):
        resp = self._del(f'/accounts/{account_id}', bank_token)
        resp_json = json.loads(resp.data)
        print(resp_json)

    # Generic for GET API that uses the BASE_URL and path, and creates the necessary auth headers using the bank_token passed
    def _get(self, path, bank_token):
        return self.http.request('GET', self.BASE_URL + path, headers = urllib3.make_headers(basic_auth = bank_token + ":"))

    def _del(self, path, bank_token):
        return self.http.request('DELETE', self.BASE_URL + path, headers = urllib3.make_headers(basic_auth = bank_token + ":"))  