import urllib3
import json
import os
from collections import defaultdict
from dotenv import load_dotenv

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
    if os.environ.get('BANK_ACCOUNT_TOKENS') != None:    
        bank_tokens = os.environ.get('BANK_ACCOUNT_TOKENS').split(',')
    else:
        print("No Bank Tokens Present")
        bank_tokens.append("")
    #  
    transactions = defaultdict(list)
    #
    teller_accounts = defaultdict()

    cert_found = True
    key_found = True

    # uses a python dict to make a blank list for the current bank_token
    for bt in bank_tokens:      
        banks[bt] = ''

    # default constructor
    def __init__(self):
        # certificate and private key to be used in GET requests
        
        if os.environ.get('CERTIFICATE') == None:
            print("Certificate file not found!")
            self.cert_found = False
        if os.environ.get('KEY') == None:
            print("Key file not found!")
            self.key_found = False
        
        if self.cert_found and self.key_found:
            self.http = urllib3.PoolManager(
                cert_file = os.environ.get('CERTIFICATE'),   
                cert_reqs = "CERT_REQUIRED",
                key_file = os.environ.get('KEY')   
            )
        else:
            print("Please pass in your Teller Certificate and Keys")

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
                    acctid .append(account['id'])
                    self.teller_accounts[account['name'] + " " + account['last_four']] = account['id']
                # adds the Account IDs to the current bank
                self.banks[bank_token] = acctid
            except Exception as e:
                print("Teller API Connection Down")

    def list_account_all_transactions(self, account_id, bank_token):
        self.transactions.clear()
        resp = self._get(f'/accounts/{account_id}/transactions', bank_token)
        resp_json = json.loads(resp.data) 
        self.transactions[account_id] = resp_json

    # function for getting the transactions for a given Acccount in a given Bank
    def list_account_auto_transactions(self, account_id, bank_token):
        resp = self._get(f'/accounts/{account_id}/transactions?count={self.TRANSACTION_COUNT}', bank_token)
        resp_json = json.loads(resp.data) 
        self.transactions[account_id] = resp_json

    # Generic for GET API that uses the BASE_URL and path, and creates the necessary auth headers using the bank_token passed
    def _get(self, path, bank_token):
        return self.http.request('GET', self.BASE_URL + path, headers = urllib3.make_headers(basic_auth = bank_token + ":"))

    def addToList(self,bank_token):
            self.bank_tokens.append(bank_token)
            for b in self.bank_tokens:      
                self.banks[b] = ''
    