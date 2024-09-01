from flask import Flask, request, render_template, redirect, current_app
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from teller import TellerClient
from actualhttp import ActualHTTPClient
import dotenv
import itertools
import os
import json
from collections import defaultdict
from database import Database
from config import DATABASE
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

# Create an instance of the Flask class
app = Flask(__name__)
auth = HTTPBasicAuth()
app.config['USERNAME'] = os.environ.get('ACTUALTELLER_USERNAME')
app.config['PASSWORD'] = generate_password_hash(os.environ.get('ACTUALTELLER_PASSWORD'))
app.config['DATABASE'] = DATABASE
app.app_context().push()
scheduler = BackgroundScheduler()

@auth.verify_password
def verify_password(username, password):
    if username == app.config['USERNAME'] and check_password_hash(app.config['PASSWORD'], password):
        return True
    return False

# Define a route for the root URL
@app.route("/", methods=['get','post'])
def index():
    teller_client = TellerClient()
    actual_client = ActualHTTPClient()
    teller_client.list_accounts()
    db = get_db()

    if len(teller_client.bank_tokens) == 0:
        print("This may be a first run or a reset")
        db.close()
        return render_template("index.html",
            TELLER_APPLICATION_ID = teller_client.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = teller_client.TELLER_ENVIRONMENT_TYPE,
            cert_found = teller_client.cert_found,
            key_found = teller_client.key_found)

    if db.check_table_data():
        print("Account mapping found")
        job = scheduler.get_job("BankImports")
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
        TRANSACTION_COUNT=teller_client.TRANSACTION_COUNT,
        cert_found = teller_client.cert_found,
        key_found = teller_client.key_found)
    else:       
        print("No Linked Accounts in File")
        negative_rows = db.get_negative_rows()
        
        db.close()
        actual_client.list_accounts()
        
        return render_template("index.html", 
            actual_accounts = actual_client.actual_accounts.keys(),
            teller_accounts = teller_client.teller_accounts,
            negative_rows = negative_rows,
            TELLER_APPLICATION_ID = teller_client.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = teller_client.TELLER_ENVIRONMENT_TYPE,
            cert_found = teller_client.cert_found,
            key_found = teller_client.key_found)

# Define a route for the form submission
@app.route('/teller_connect', methods=['GET', 'POST'])
def teller_connect():
    teller_client = TellerClient()
    actual_client = ActualHTTPClient()

    bank = defaultdict()
    # Get tokens from the webpage
    teller_tokens = request.form.getlist('teller_token')

    db = get_db()
    for tt in teller_tokens:
        bank, token = tt.split(',')
        db.insert_token(bank,token)
    db.close()
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
            db.insert_item(name, actual_account, teller_account, (int(neg)), (int(is_mapped)))

        linked_actual_teller_accounts = []
        unlinked_actual_teller_accounts = []
        items = db.view_items()
        print("All items:")
        for item in items:
            if bool(item[5]):
                linked_actual_teller_accounts.append(item[1])
            else:
                unlinked_actual_teller_accounts.append(item[1])

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
    print("Importing in process...")
    teller_client = TellerClient()
    db = get_db()

    data = request.get_json()
    actual_account, teller_account, isNeg = db.get_accounts_by_name(data["account"])

    db.close()

    linked_token = get_bank_token(teller_account)
    teller_client.list_account_all_transactions(teller_account, linked_token)
    actual_request = teller_tx_to_actual_tx(actual_account, teller_account, isNeg)
    print("Import complete")
    return "Import complete"    

def teller_tx_to_actual_tx(actual_account, teller_account, isNeg):
    teller_client = TellerClient()
    transactions = teller_client.transactions[teller_account]
    transaction_batches = []
    batch_size = 10
    if (len(transactions) == 0):
        print("No Transactions on this Account")
        return

    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i+batch_size]
        transaction_batches.append(batch)

    for batch in transaction_batches:
        request_body = ""
        last_transaction = batch[-1]
        for tx in batch:      
            # This will be used to determine if the amount should be multiplied by -1, as some bank amount are negative
            amount = int(float(tx["amount"]) * (100 if isNeg else -100))
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
        transaction_to_actual(request_body, actual_account)

def get_bank_token(account):
    tc = TellerClient()
    token = ''
    # print(tc.bank_tokens)
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
        # scheduler.add_job(get_transactions_and_import, "cron", minute="*/5", id="BankImports")
        scheduler.start()
        print("Scheduler is now running")
        job = scheduler.get_job("BankImports")
        # Prints the next run for imports in a YYYY-MM-DD HH:MM:SS format
        print(f"Next run time for Imports: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)
    return redirect('/')

# This stops the Automatic Importing
@app.route('/stop_schedule', methods = ['POST'])
def stop_schedule():
    try:
        scheduler.remove_job("BankImports")   
        scheduler.shutdown()   
    except Exception as e:
        print(e)
    return redirect('/')

# This is the function called to do the Get Requests from Teller and Post Request into ActualHTTPAPI
def get_transactions_and_import():
    with app.app_context():
        teller_client = TellerClient()
        db = get_db()
        linked_accounts = db.get_all_linked_accounts()
        db.close()        
        for name, actual_account, teller_account, isNeg  in linked_accounts:
            teller_client.transactions.clear()
            linked_token = get_bank_token(teller_account)
            teller_client.list_account_auto_transactions(teller_account, linked_token)
            print(f'Import beginning for Account: {name}')
            actual_request = teller_tx_to_actual_tx(actual_account, teller_account, isNeg)
            print('Import Complete')
        print("Scheduled task is completed")
    # Prints the next run for imports in a YYYY-MM-DD HH:MM:SS format
    job = scheduler.get_job("BankImports")
    print(f"Next run time for Imports: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
  
def transaction_to_actual(request_body, account): 
    client = ActualHTTPClient()
    # Adds the following to the request to fit what is expected in a request
    request_body = '{"transactions":[' + request_body + ']}'
    # Import transaction to Actual
    client.import_transactions(account,request_body)

def get_db():
    return Database(app.config['DATABASE'])

# calls main()
if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=True, port=5000, host='0.0.0.0')

    