from flask import Flask, request, render_template, redirect, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from teller import TellerClient
from actualhttp import ActualHTTPClient
import dotenv
import itertools
import os
import json
from collections import defaultdict
import pickle

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

# Create an instance of the Flask class
app = Flask(__name__)
app.config['SECRET_KEY'] = 'N8wwf$k*ubKrL8euub5$Lg!Z4gy7j^v5'
scheduler = BackgroundScheduler()

# Define a route for the root URL
@app.route("/", methods=['get','post'])
def index():
    teller_client = TellerClient()
    actual_client = ActualHTTPClient()
    teller_client.list_accounts()
    
    if teller_client.bank_tokens[0] == "":
        print("This may be a first run or a reset")
        return render_template("index.html",
            TELLER_APPLICATION_ID = teller_client.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = teller_client.TELLER_ENVIRONMENT_TYPE)

    if is_pickle_not_empty("./data/AccountMaps.pkl"):
        print("Account mapping found")
        job = scheduler.get_job("BankImports")
        print(job)
        if job:
            button_status = "disabled"
            btn_stop_status = "enabled"
        else:
            button_status = "enabled"
            btn_stop_status = "disabled"

        # Opens the pickle file in read bytes
        f = open("./data/AccountMaps.pkl", "rb")
        linked_accounts = pickle.load(f)
        unlinked_accounts = pickle.load(f)
        f.close()

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linked_accounts, f)
        pickle.dump(unlinked_accounts,f)
        f.close()  

        return render_template("linked_accounts.html", 
        linked_accounts=linked_accounts.keys(),
        unlinked_accounts=unlinked_accounts.keys(),
        button_status = button_status,
        btn_stop_status = btn_stop_status,
        TRANSACTION_COUNT=teller_client.TRANSACTION_COUNT)

    else:       
        print("No Linked Accounts in File")
        teller_client.list_accounts()
        print(teller_client.bank_tokens)

        actual_client = ActualHTTPClient()
        actual_client.list_accounts()
        
        return render_template("index.html", 
            actual_accounts = actual_client.actual_accounts.keys(),
            teller_accounts = teller_client.teller_accounts,
            TELLER_APPLICATION_ID = teller_client.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = teller_client.TELLER_ENVIRONMENT_TYPE)

# Define a route for the form submission
@app.route('/teller_connect', methods=['GET', 'POST'])
def teller_connect():
    teller_client = TellerClient()
    actual_client = ActualHTTPClient()
    if teller_client.bank_tokens[0] == "":
        teller_client.bank_tokens.pop(0)

    # Get tokens from the webpage
    teller_tokens = request.form.getlist('teller_token')
    print("HTML teller_tokens")
    print(teller_tokens)
    # Get tokens from the env file
    env_tokens = os.environ["BANK_ACCOUNT_TOKENS"]
    if (env_tokens != ""):
        env_tokens += ","
    
    # For each token submitted, add it to the list of bank tokens
    # Useful during runtime, as adding to the env file doesn't work unless the program is restarted
    for tt in teller_tokens:
        env_tokens += tt + ","
        teller_client.addToList(tt)

    # This removes the last character from the envtokens above since it will always end with a ,
    os.environ["BANK_ACCOUNT_TOKENS"] = env_tokens[:-1]
    # Saves changes to the env file, however this will only take affect if app is restarted
    dotenv.set_key(dotenv_file, "BANK_ACCOUNT_TOKENS", os.environ["BANK_ACCOUNT_TOKENS"])

    print("teller_client bank tokens")
    print(teller_client.bank_tokens)
    
    return redirect('/')

# Define a route for the form submission
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        # Recreates the teller_client and actual_clients
        teller_client = TellerClient()
        actual_client = ActualHTTPClient()  

        # Instantiates a dictionary to hold the result from the form
        actual_teller_results = defaultdict()         
        
        # Since the form only has actual_accounts that are displayed
        # This loop sets the actualTellerResult dictionary to what was selected in the form
        for actual_account in actual_client.actual_accounts.keys():               
            print(request.form.get(f'account-select-{actual_account}')) 
            actual_teller_results[actual_account] = request.form.get(f'account-select-{actual_account}')

        linked_actual_teller_accounts = defaultdict(list)
        unlinked_actual_teller_accounts = defaultdict(list)

        for account, id in actual_client.actual_accounts.items():
            if actual_teller_results[account] != '':
                linked_actual_teller_accounts[account] = [id, actual_teller_results[account]]
            else:   
                unlinked_actual_teller_accounts[account] = [id, ""]

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linked_actual_teller_accounts, f)
        pickle.dump(unlinked_actual_teller_accounts,f)
        f.close()  

        return render_template("submit_linking.html", 
            linked_actual_teller_accounts=linked_actual_teller_accounts.keys(),
            unlinked_actual_teller_accounts=unlinked_actual_teller_accounts.keys())
    else:
        return 'Method not allowed', 405

# When Reset Links is clicked, then this removes all data from the pickle
@app.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == 'GET':
        f = open("./data/AccountMaps.pkl", "r+b")
        f.truncate(0)
        f.close()
        print("Reseting links")
        return redirect('/')
    else:
        return 'Method not allowed', 405

# This redirects from the after import page back to index
@app.route('/continue_import')
def continue_import():
    return redirect('/')

@app.route('/import', methods=['POST'])
def importTransactions():
    teller_client = TellerClient()

    f = open("./data/AccountMaps.pkl", "rb")
    linked_accounts = pickle.load(f)
    unlinked_accounts = pickle.load(f)
    f.close()

    f = open("./data/AccountMaps.pkl", 'wb')    
    pickle.dump(linked_accounts, f)
    pickle.dump(unlinked_accounts,f)
    f.close()   
    
    data = request.get_json()
    account = linked_accounts[data["account"]]
    linked_token = get_bank_token(account[1])
    teller_client.list_account_all_transactions(account[1], linked_token)

    actual_request = teller_tx_to_actual_tx(account)
    if actual_request == "No Transactions on this Account":
        print(actual_request)
    else:
        transaction_to_actual(actual_request, account[0])

    return "Import complete"

def teller_tx_to_actual_tx(account):
    teller_client = TellerClient()
    request_body = ""
    try:     
        print(teller_client.transactions)
        transactions = teller_client.transactions[account[1]]
        last_transaction = list(transactions)[-1]   
        for tx in transactions:
            # This will be used to determine if the amount should be multiplied by -1, as some bank amount are negative
            amount = int(float(tx["amount"]) * -100)
            # Json that will be sent to Actual
            body = {
                "account": account[0],
                "amount": amount,
                "payee_name": tx["description"],
                "date": tx["date"]
            }            
            request_body += json.dumps(body)
            # If it's the last Transaction don't append with the ","
            if last_transaction != tx:
                request_body += ","
        return(request_body)
    except Exception as e:
        return("No Transactions on this Account")

def get_bank_token(account):
    tc = TellerClient()
    token = ''
    for bank_token, connection in tc.banks.items():       
        if account in connection:
            token = bank_token
            break
    return bank_token

# This starts the Automatic Importing
@app.route('/start_schedule', methods = ['POST'])
def start_schedule():    
    try:
        # run everyday at midnight
        scheduler.add_job(get_transactions_and_import, "cron", hour="0", id="BankImports")
        # scheduler.add_job(get_transactions_and_import, "cron", second="*/30", id="BankImports")
        scheduler.start()
        print("Scheduler is now running")
    except Exception as e:
        print(e)
    return redirect('/')

# This stops the Automatic Importing
@app.route('/stop_schedule', methods = ['POST'])
def stop_schedule():
    try:
        scheduler.remove_job("BankImports")      
    except Exception as e:
        print(e)
    return redirect('/')

# This is the function called to do the Get Requests from Teller and Post Request into ActualHTTPAPI
def get_transactions_and_import():
    teller_client = TellerClient()
    ## This block loads what's in the pickle, and dumps it back into the pickle, just used to get current data
    f = open("./data/AccountMaps.pkl", "rb")
    linked_accounts = pickle.load(f)
    unlinked_accounts = pickle.load(f)
    f.close()

    f = open("./data/AccountMaps.pkl", 'wb')    
    pickle.dump(linked_accounts, f)
    pickle.dump(unlinked_accounts,f)
    f.close()

    # Clears the current transactions
    teller_client.transactions.clear()
    # This loops through all Linked Accounts and gets the transactions for auto imports
    print(linked_accounts)
    for id, linkedAccount in linked_accounts.items():
        linked_token = get_bank_token(linkedAccount[1])           
        teller_client.list_account_auto_transactions(linkedAccount[1], linked_token)
        actual_request = teller_tx_to_actual_tx(linkedAccount)
        if actual_request == "No Transactions on this Account":
            print(actual_request)
        else:
            transaction_to_actual(actual_request, linkedAccount[0])      
  
def transaction_to_actual(request_body, account): 
    client = ActualHTTPClient()
    # Adds the following to the request to fit what is expected in a request
    request_body = '{"transactions":[' + request_body + ']}'
    # Import transaction to Actual
    client.import_transactions(account,request_body)

# This checks if there is any data in the pickle file
def is_pickle_not_empty(file_name):
    try:
        file_stat = os.stat(file_name)
        return file_stat.st_size > 0
    except Exception as e:
        print(e)
        return False

# calls main()
if __name__ == '__main__':
    app.run(debug=True, port=8001, host='0.0.0.0')