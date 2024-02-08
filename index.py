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
    tellerclient = TellerClient()
    actualclient = ActualHTTPClient()
    tellerclient.list_accounts()
    
    if tellerclient.bankTokens[0] == "":
        print("This may be a first run or a reset")
        return render_template("index.html",
            TELLER_APPLICATION_ID = tellerclient.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = tellerclient.TELLER_ENVIRONMENT_TYPE)

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
        linkedAccounts = pickle.load(f)
        unlinkedAccounts = pickle.load(f)
        f.close()

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linkedAccounts, f)
        pickle.dump(unlinkedAccounts,f)
        f.close()  

        return render_template("linkedAccounts.html", 
        linkedAccounts=linkedAccounts.keys(),
        unlinkedAccounts=unlinkedAccounts.keys(),
        button_status = button_status,
        btn_stop_status = btn_stop_status,
        TRANSACTION_COUNT=tellerclient.TRANSACTION_COUNT)

    else:       
        print("No Linked Accounts in File")
        tellerclient.list_accounts()
        print(tellerclient.bankTokens)

        actualclient = ActualHTTPClient()
        actualclient.list_accounts()
        
        return render_template("index.html", 
            actualAccounts = actualclient.actualAccounts.keys(),
            tellerAccounts = tellerclient.tellerAccounts,
            TELLER_APPLICATION_ID = tellerclient.TELLER_APPLICATION_ID,
            TELLER_ENVIRONMENT_TYPE = tellerclient.TELLER_ENVIRONMENT_TYPE)

# Define a route for the form submission
@app.route('/tellerconnect', methods=['GET', 'POST'])
def tellerconnect():
    tellerclient = TellerClient()
    actualclient = ActualHTTPClient()
    if tellerclient.bankTokens[0] == "":
        tellerclient.bankTokens.pop(0)

    # Get tokens from the webpage
    tellertokens = request.form.getlist('tellertoken')
    print("HTML tellertokens")
    print(tellertokens)
    # Get tokens from the env file
    envTokens = os.environ["BANK_ACCOUNT_TOKENS"]
    if (envTokens != ""):
        envTokens += ","
    
    # For each token submitted, add it to the list of bank tokens
    # Useful during runtime, as adding to the env file doesn't work unless the program is restarted
    for tt in tellertokens:
        envTokens += tt + ","
        tellerclient.addToList(tt)

    # This removes the last character from the envtokens above since it will always end with a ,
    os.environ["BANK_ACCOUNT_TOKENS"] = envTokens[:-1]
    # Saves changes to the env file, however this will only take affect if app is restarted
    dotenv.set_key(dotenv_file, "BANK_ACCOUNT_TOKENS", os.environ["BANK_ACCOUNT_TOKENS"])

    print("Tellerclient bank tokens")
    print(tellerclient.bankTokens)
    
    return redirect('/')

# Define a route for the form submission
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        # Recreates the tellerclient and actualclients
        tellerclient = TellerClient()
        actualclient = ActualHTTPClient()  

        # Instantiates a dictionary to hold the result from the form
        actualTellerResults = defaultdict()         
        
        # Since the form only has actualAccounts that are displayed
        # This loop sets the actualTellerResult dictionary to what was selected in the form
        for actualAccount in actualclient.actualAccounts.keys():               
            print(request.form.get(f'account-select-{actualAccount}')) 
            actualTellerResults[actualAccount] = request.form.get(f'account-select-{actualAccount}')

        linkedActualTellerAccounts = defaultdict(list)
        unlinkedActualTellerAccounts = defaultdict(list)

        for account, id in actualclient.actualAccounts.items():
            if actualTellerResults[account] != '':
                linkedActualTellerAccounts[account] = [id, actualTellerResults[account]]
            else:   
                unlinkedActualTellerAccounts[account] = [id, ""]

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linkedActualTellerAccounts, f)
        pickle.dump(unlinkedActualTellerAccounts,f)
        f.close()  

        return render_template("submitLinking.html", 
            linkedActualTellerAccounts=linkedActualTellerAccounts.keys(),
            unlinkedActualTellerAccounts=unlinkedActualTellerAccounts.keys())
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
@app.route('/continueImport')
def continueImport():
    return redirect('/')

@app.route('/import', methods=['POST'])
def importTransactions():
    tellerclient = TellerClient()

    f = open("./data/AccountMaps.pkl", "rb")
    linkedAccounts = pickle.load(f)
    unlinkedAccounts = pickle.load(f)
    f.close()

    f = open("./data/AccountMaps.pkl", 'wb')    
    pickle.dump(linkedAccounts, f)
    pickle.dump(unlinkedAccounts,f)
    f.close()    
    
    data = request.get_json()
    account = linkedAccounts[data["account"]]
    linkedToken = getBankToken(account[1])
    tellerclient.list_account_all_transactions(account[1], linkedToken)

    actualRequest = tellerTxToActualTx(account)
    if actualRequest == "No Transactions on this Account":
        print(actualRequest)
    else:
        transactionToActual(actualRequest, account[0])

    return "Import complete"

def tellerTxToActualTx(account):
    tellerclient = TellerClient()
    requestBody = ""
    try:     
        print(tellerclient.transactions)
        transactions = tellerclient.transactions[account[1]]
        last_Transaction = list(transactions)[-1]   
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
            requestBody += json.dumps(body)
            # If it's the last Transaction don't append with the ","
            if last_Transaction != tx:
                requestBody += ","
        return(requestBody)
    except Exception as e:
        return("No Transactions on this Account")

def getBankToken(account):
    tc = TellerClient()
    token = ''
    for bankToken, connection in tc.banks.items():       
        if account in connection:
            token = bankToken
            break
    return bankToken

# This starts the Automatic Importing
@app.route('/start_schedule', methods = ['POST'])
def startSchedule():    
    try:
        # run everyday at midnight
        scheduler.add_job(getTransactionsAndImport, "cron", hour="0", id="BankImports")
        # scheduler.add_job(getTransactionsAndImport, "cron", second="*/30", id="BankImports")
        scheduler.start()
        print("Scheduler is now running")
    except Exception as e:
        print(e)
    return redirect('/')

# This stops the Automatic Importing
@app.route('/stop_schedule', methods = ['POST'])
def stopSchedule():
    try:
        scheduler.remove_job("BankImports")      
    except Exception as e:
        print(e)
    return redirect('/')

# This is the function called to do the Get Requests from Teller and Post Request into ActualHTTPAPI
def getTransactionsAndImport():
    tellerclient = TellerClient()
    ## This block loads what's in the pickle, and dumps it back into the pickle, just used to get current data
    f = open("./data/AccountMaps.pkl", "rb")
    linkedAccounts = pickle.load(f)
    unlinkedAccounts = pickle.load(f)
    f.close()

    f = open("./data/AccountMaps.pkl", 'wb')    
    pickle.dump(linkedAccounts, f)
    pickle.dump(unlinkedAccounts,f)
    f.close()

    # Clears the current transactions
    tellerclient.transactions.clear()
    # This loops through all Linked Accounts and gets the transactions for auto imports
    print(linkedAccounts)
    for id, linkedAccount in linkedAccounts.items():
        linkedToken = getBankToken(linkedAccount[1])           
        tellerclient.list_account_auto_transactions(linkedAccount[1], linkedToken)
        actualRequest = tellerTxToActualTx(linkedAccount)
        if actualRequest == "No Transactions on this Account":
            print(actualRequest)
        else:
            transactionToActual(actualRequest, linkedAccount[0])      
  
def transactionToActual(requestBody, account): 
    client = ActualHTTPClient()
    # Adds the following to the request to fit what is expected in a request
    requestBody = '{"transactions":[' + requestBody + ']}'
    # Import transaction to Actual
    client.import_transactions(account,requestBody)

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