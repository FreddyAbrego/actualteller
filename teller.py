import urllib3
import json
import os
from collections import defaultdict
from dotenv import load_dotenv

# Searches for .env file 
load_dotenv()
class TellerClient:
    
    BASE_URL = "https://api.teller.io/"

    # python dict to hold lists
    banks = defaultdict(list)
    # splits the account tokens CHANGE TELLER_ACCOUNTS TO BANK TOKENS
    try:
        bankTokens = os.environ.get('BANK_ACCOUNT_TOKENS').split(',')
    except Exception as e:
        bankTokens = ['']
    #  
    transactions = defaultdict(list)
    #
    tellerAccounts = defaultdict()

    # uses a python dict to make a blank list for the current bankToken
    for b in bankTokens:      
        banks[b] = ''

    # default constructor
    def __init__(self):
        # certificate and private key to be used in GET requests
        self.http = urllib3.PoolManager(
            cert_file = os.environ.get('CERTIFICATE'),   
            cert_reqs = "CERT_REQUIRED",
            key_file = os.environ.get('KEY')   
        )

    # function for getting the account ids
    def list_accounts(self, bankToken):
        try:
            # resp is the response of a GET for accounts using the bankToken for the header
            resp = self._get(f'/accounts', bankToken)
            # uses json.loads to change format to json
            respJson = json.loads(resp.data)
            # empty list to add the Account IDs that are associated with certain bank
            acctid = []
            # loops for every account found in the linked bank
            for account in respJson:
                acctid .append(account['id'])
                self.tellerAccounts[account['name'] + " " + account['last_four']] = account['id']
            # adds the Account IDs to the current bank
            self.banks[bankToken] = acctid
        except Exception as e:
            print("Teller API Connection Down")

    # function for getting the transactions for a given Acccount in a given Bank
    def list_account_transactions(self, account_id, bankToken):
        
        resp = self._get(f'/accounts/{account_id}/transactions?count=1', bankToken)
        # self.http.request('GET', self.BASE_URL + "/accounts/" + accountid + "/transactions", headers=headers)
        respJson = json.loads(resp.data)    
        self.transactions[account_id] = respJson

    # Generic for GET API that uses the BASE_URL and path, and creates the necessary auth headers using the bankToken passed
    def _get(self, path, bankToken):
        return self.http.request('GET', self.BASE_URL + path, headers = urllib3.make_headers(basic_auth = bankToken + ":"))


    