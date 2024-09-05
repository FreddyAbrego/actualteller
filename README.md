# actualTeller

# Setup
- Create Teller.io developer Account
- If you are using the .env file, change ".env." to ".env" and and fill in the blanks.
- If you are using the docker-compose, fill in your info within that file instead.
- You will have to connect your bank in app. 
- You can perform a manual import first as it will grab all available data.
- Check the bank payment/amount in Actual to see if the pulls should be multiplied by negative 1, if so click the checkbox next to Transaction to do so.
- From my findings Checking and Savings accounts would be multiplied by negative 1, while Credit Cards wouldn't be, but it could differ by th bank you use.

# Some things worth noting
- You need actual budget accounts in order to link it
- The first initial import does not have a starting balance, you will need to balance it out first.
- The order of the Actual Accounts seems to be the order in which they are created, not the order of the WebGUI. I recommend not using the same name for different accounts

# About
This application will connect ActualBudget and Teller.io and uses Actual-HTTP-API in order to use the Actual API. 