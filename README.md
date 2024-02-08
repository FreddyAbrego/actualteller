# actualTeller

# Setup
- Create Teller.io developer Account
- Change .env. to .env and and fill in the blanks
- You will have to connect your bank in app. Make sure the TELLER_ENVIRONMENT_TYPE is set to development in your env file
- Do a manual import first as it will grab all available data
- Check the bank payment/amount in Actual to see if the pulls should be multiplied by negative 1
- Set the TRANSACTION_COUNT env to the amount of transactions it should automatically grab. I put 60 as the default but change based on your spending habits.

# Some things worth noting
- You need actual budget accounts in order to link it
- Actual account names should be unique
- The first initial import does not have a starting balance, you will need to balance it out first.

# About
This application will connect ActualBudget and Teller.io and uses HTTPAPI in order to use the Actual API. 