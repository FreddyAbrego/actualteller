from flask import Flask, request, render_template, redirect, current_app
from apscheduler.schedulers.background import BackgroundScheduler
from teller import TellerClient
from actualhttp import ActualHTTPClient
import dotenv
import itertools
import os
import json
from collections import defaultdict
from database import Database
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

# Create an instance of the Flask class
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ACTUAL_TELLER_SECRET_KEY')
app.config['DATABASE'] = './data/account_maps.db'
app.app_context().push()
scheduler = BackgroundScheduler()

# Define a route for the root URL
@app.route("/", methods=['get','post'])
def index():
    teller_client = TellerClient()
    actual_client = ActualHTTPClient()
    teller_client.list_accounts()
    db = get_db()

    if teller_client.bank_tokens[0] == "":
        print("This may be a first run or a reset")
        db.close()
        return render_template("index.html",
            TELLER_APPLICATION_ID = teller_client.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = teller_client.TELLER_ENVIRONMENT_TYPE)

    if db.check_table_data():
        print("Account mapping found")
        job = scheduler.get_job("BankImports")
        print(job)
        if job:
            button_status = "disabled"
            btn_stop_status = "enabled"
        else:
            button_status = "enabled"
            btn_stop_status = "disabled"
        
        linked_accounts = db.get_linked_accounts_names()
        unlinked_accounts = db.get_unlinked_accounts_names()
        
        db.close()
        return render_template("linked_accounts.html", 
        linked_accounts=linked_accounts,
        unlinked_accounts=unlinked_accounts,
        button_status = button_status,
        btn_stop_status = btn_stop_status,
        TRANSACTION_COUNT=teller_client.TRANSACTION_COUNT)
    else:       
        print("No Linked Accounts in File")
        db.close()
        teller_client.list_accounts()

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
        db = get_db()
        # Recreates the teller_client and actual_clients
        teller_client = TellerClient()
        actual_client = ActualHTTPClient()  

        # Instantiates a dictionary to hold the result from the form
        actual_teller_results = defaultdict()
        for account, id in actual_client.actual_accounts.items():
            name = account
            actual_account = id
            teller_account = request.form.get(f'account-select-{account}')
            neg = True if request.form.get(f'{account}-is-negative') else False
            is_mapped = False if teller_account == '' else True
            # print(f'Statement will contain, {name}, {actual_account}, {teller_account}, {(int(neg))}, {(int(is_mapped))}')
            # print(f'Datatype name: {type(name)}, actual_account: {type(actual_account)}, teller_account: {type(teller_account)}, neg: {type((int(neg)))}, is_mapped: {type((int(is_mapped)))}')
            db.insert_item(name, actual_account, teller_account, (int(neg)), (int(is_mapped)))

        linked_actual_teller_accounts = []
        unlinked_actual_teller_accounts = []
        # items = db.view_items()
        # print("All items:")
        # for item in items:
        #     if bool(item[5]):
        #         print("IT'S MAPPED")
        #         print(item)
        #         linked_actual_teller_accounts.append(item[1])
        #     else:
        #         print("IT'S NOT MAPPED")
        #         print(item)
        #         unlinked_actual_teller_accounts.append(item[1])

        db.close()

        return render_template("submit_linking.html", 
            linked_actual_teller_accounts=linked_actual_teller_accounts,
            unlinked_actual_teller_accounts=unlinked_actual_teller_accounts)
    else:
        return 'Method not allowed', 405

# When Reset Links is clicked, then this removes all data from the database table
@app.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == 'GET':
        db = get_db()
        db.reset()
        db.close()
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
    db = get_db()

    data = request.get_json()
    actual_account, teller_account = db.get_accounts_by_name(data["account"])

    db.close()
    
    linked_token = get_bank_token(teller_account)
    teller_client.list_account_all_transactions(teller_account, linked_token)
    actual_request = teller_tx_to_actual_tx(actual_account, teller_account)
    if actual_request == "No Transactions on this Account":
        print(actual_request)
    else:
        transaction_to_actual(actual_request, actual_account)

    return "Import complete"    

def teller_tx_to_actual_tx(actual_account, teller_account):
    teller_client = TellerClient()
    request_body = ""
    try:     
        print(teller_client.transactions)
        transactions = teller_client.transactions[teller_account]
        last_transaction = list(transactions)[-1]   
        for tx in transactions:
            # This will be used to determine if the amount should be multiplied by -1, as some bank amount are negative
            amount = int(float(tx["amount"]) * -100)
            # Json that will be sent to Actual
            body = {
                "account": actual_account,
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
        
        # scheduler.add_job(get_transactions_and_import, "cron", second="*/10", id="BankImports")
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
    with app.app_context():
        teller_client = TellerClient()
        db = get_db()

        # data = request.get_json()
        # actual_account, teller_account = db.get_accounts_by_name(data["account"])
        linked_accounts = db.get_all_linked_accounts()
        
        db.close()

        for actual_account,teller_account  in linked_accounts:
            teller_client.transactions.clear()
            linked_token = get_bank_token(teller_account)       
            teller_client.list_account_auto_transactions(teller_account, linked_token)
            actual_request = teller_tx_to_actual_tx(actual_account, teller_account)
            if actual_request == "No Transactions on this Account":
                print(actual_request)
            else:
                transaction_to_actual(actual_request, actual_account)

            # print(teller_account)
            # print(actual_account)

        # Clears the current transactions
        # teller_client.transactions.clear()
        # This loops through all Linked Accounts and gets the transactions for auto imports
        
        # for id, linkedAccount in linked_accounts.items():
        #     linked_token = get_bank_token(teller_account)           
        #     teller_client.list_account_auto_transactions(teller_account, linked_token)
        #     actual_request = teller_tx_to_actual_tx(linkedAccount)
        #     if actual_request == "No Transactions on this Account":
        #         print(actual_request)
        #     else:
        #         transaction_to_actual(actual_request, actual_account)      
  
def transaction_to_actual(request_body, account): 
    client = ActualHTTPClient()
    # Adds the following to the request to fit what is expected in a request
    request_body = '{"transactions":[' + request_body + ']}'
    # Import transaction to Actual
    client.import_transactions(account,request_body)

def get_db():
    return Database(app.config['DATABASE'])

# def close_db(db):
#     db.close()
    
# @app.teardown_appcontext
# def teardown_db(error=None):
#     close_db()

# calls main()
if __name__ == '__main__':
    app.run(debug=True, port=8001, host='0.0.0.0')