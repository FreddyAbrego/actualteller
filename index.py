# Import the Flask library
from flask import Flask, request, render_template, redirect
from apscheduler.schedulers.background import BackgroundScheduler
from teller import TellerClient
from actualhttp import ActualHTTPClient
import itertools
import os
import json
from collections import defaultdict
import pickle

# Create an instance of the Flask class
app = Flask(__name__)
app.config['SECRET_KEY'] = 'N8wwf$k*ubKrL8euub5$Lg!Z4gy7j^v5'
scheduler = BackgroundScheduler()

# Define a route for the root URL
@app.route("/", methods=['get','post'])
def index():
    if is_pickle_not_empty("./data/AccountMaps.pkl"):
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

        # print("Linked Accounts")
        # print(linkedAccounts)
        # print("Unlinked Accounts")
        # print(unlinkedAccounts)

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linkedAccounts, f)
        pickle.dump(unlinkedAccounts,f)
        f.close()  

        return render_template("linkedAccounts.html", 
        linkedAccounts=linkedAccounts.keys(),
        unlinkedAccounts=unlinkedAccounts.keys(),
        button_status = button_status,
        btn_stop_status = btn_stop_status)

    else:       
        print("No Linked Accounts")
        # Render a template that contains a form
        tellerclient = TellerClient()

        for bank, accountid in tellerclient.banks.items():
            tellerclient.list_accounts(bank)

        # for bank, accounts in tellerclient.banks.items():
        #     for account in accounts:
        #         tellerclient.list_account_transactions(account, bank)

        actualclient = ActualHTTPClient()
        actualclient.list_accounts()

        f = open('./data/links.pkl', 'wb')    
        pickle.dump(tellerclient.banks, f)
        pickle.dump(tellerclient.tellerAccounts,f)
        pickle.dump(actualclient.actualAccounts, f)
        f.close()    
        
        return render_template("index.html", 
            actualAccounts = actualclient.actualAccounts.keys(),
            tellerAccounts = tellerclient.tellerAccounts)

# Define a route for the form submission
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        # Recreates the tellerclient and actualclients
        tellerclient = TellerClient()
        actualclient = ActualHTTPClient()  

        # Opens the pickle file in read bytes
        f = open("./data/links.pkl", "rb")

        # Sets the TellerClient banks to what was first put into the pickle
        tellerclient.banks = pickle.load(f)

        # Sets the TellerClient accounts to what was put into the pickle next
        tellerclient.tellerAccounts = pickle.load(f)
        
        # Sets the ActualClient accounts to what was last put into the pickle
        actualclient.actualAccounts = pickle.load(f)

        # Closes connection to the pickle
        f.close()

        f = open("./data/links.pkl", "wb")
        pickle.dump(tellerclient.banks,f)
        pickle.dump(tellerclient.tellerAccounts,f)
        pickle.dump(actualclient.actualAccounts,f)
        f.close()

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
        
        # print("Linked Accounts")
        # print(linkedActualTellerAccounts)
        # print("Unlinked Accounts")
        # print(unlinkedActualTellerAccounts)

        f = open("./data/AccountMaps.pkl", 'wb')    
        pickle.dump(linkedActualTellerAccounts, f)
        pickle.dump(unlinkedActualTellerAccounts,f)
        f.close()  

        return render_template("submitLinking.html", 
            linkedActualTellerAccounts=linkedActualTellerAccounts.keys(),
            unlinkedActualTellerAccounts=unlinkedActualTellerAccounts.keys())
    else:
        return 'Method not allowed', 405

@app.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == 'GET':
        f = open("./data/AccountMaps.pkl", "r+b")
        f.truncate(0)
        f.close()
        f = open("./data/links.pkl", "r+b")
        f.truncate(0)
        f.close()
        print("Reseting links")
        return redirect('/')
    else:
        return 'Method not allowed', 405

@app.route('/continueImport')
def continueImport():
    return redirect('/')

@app.route('/import', methods=['GET','POST'])
def importTransactions():
    
    return render_template("linkedAccounts.html")

@app.route('/start_schedule', methods = ['POST'])
def startSchedule():    
    try:
        # change from minute="*/5" to test every 5 minutes
        # scheduler.add_job(getTransactions, "cron", hour="*", args=[accountsToImport], id="BankImports")
        scheduler.add_job(getTransactionsAndImport, "cron", second="*/15", id="BankImports")
        scheduler.start()
        print("Scheduler is now running")
    except Exception as e:
        print(e)
    return redirect('/')

@app.route('/stop_schedule', methods = ['POST'])
def stopSchedule():
    try:
        scheduler.remove_job("BankImports")      
    except Exception as e:
        print(e)
    return redirect('/')

i = 0
def getTransactionsAndImport():
    tellerclient = TellerClient()
    actualclient = ActualHTTPClient()
    # Opens the pickle file in read bytes
    f = open("./data/AccountMaps.pkl", "rb")
    linkedAccounts = pickle.load(f)
    unlinkedAccounts = pickle.load(f)
    f.close()

    f = open("./data/AccountMaps.pkl", 'wb')    
    pickle.dump(linkedAccounts, f)
    pickle.dump(unlinkedAccounts,f)
    f.close()

    f = open("./data/links.pkl", "rb")
    tellerclient.banks = pickle.load(f)
    tellerclient.tellerAccounts = pickle.load(f)
    actualclient.actualAccounts = pickle.load(f)
    f.close()

    f = open("./data/links.pkl", "wb")
    pickle.dump(tellerclient.banks,f)
    pickle.dump(tellerclient.tellerAccounts,f)
    pickle.dump(actualclient.actualAccounts,f)
    f.close()
    for id, linkedAccount in linkedAccounts.items():
        linkedToken = ""
        for token, connection in tellerclient.banks.items():
            if linkedAccount[1] in connection:
                linkedToken = token
                break
        tellerclient.list_account_auto_transactions(linkedAccount[1], linkedToken)
    
    # print("Linked Accounts:")
    # print(linkedAccounts)
    requestBody = ""
    last_Account = list(tellerclient.transactions)[-1]
    last_Transaction = tellerclient.transactions[last_Account][-1]
    # print(f'LAST ACCOUNT: {last_Account}')
    # print(f'LAST TRANSACTION: {last_Transaction}')
    for account, transactions in tellerclient.transactions.items():
        last_Transaction = list(transactions)[-1]
        # print(f'LAST TRANSACTION: {last_Transaction}')
        for tx in transactions:
            actualAccount = ""
            # print(f'Transaction for account: {account}: {tx}')
            # print(tx)
            for id, linkedAccount in linkedAccounts.items():
                if linkedAccount[1] in tx["account_id"]:
                    actualAccount = linkedAccount[0]
                    break
                    # print(f'Actual account: {linkedAccount[0]}')
                    
                    # requestBody += json.dumps(body) 
                    # if tx["account_id"] != last_Transaction:
                    #     requestBody += "," 
            body = {
                "account": actualAccount,
                "amount": int(float(tx["amount"]) * 100),
                "payee_name": tx["description"],
                "date": tx["date"]
            }            
            requestBody += json.dumps(body)
            
            if last_Transaction != tx or last_Account != account:
                # print("I made it here")
                requestBody += ","
    transactionToActual(requestBody, actualclient, linkedAccounts)
    # for id, linkedAccount in linkedAccounts.items():
    #     actualAccount = ""
    #     for account, transactions in tellerclient.transactions.items():
    #         if linkedAccount[1] in account:
    #             print(f'Actual account: {linkedAccount[0]}')  



            
            # # print(f'Teller account: {account}')      
            # for tx in transactions:
            #     print(tx)
            #     if linkedAccount[1] in tx:
            #         # print(f'Actual account: {linkedAccount[0]}')    
            #         body = {
            #             "account": linkedAccount[0],
            #             "amount": int(float(tx["amount"]) * 100),
            #             "payee_name": tx["description"],
            #             "date": tx["date"]
            #         }

            #         requestBody += json.dumps(body)

            #     if account != last_Account:
            #         requestBody += "," 

    # transactionToActual(requestBody)

def transactionToActual(requestBody, client, linkedAccounts):
    # print("Request for Actual:")
    # print(requestBody)
    for id, account in client.actualAccounts.items():
        print(f'ID: {id} and Account: {account}')
        print(f'ID: {id} and linkedAccount')
    


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