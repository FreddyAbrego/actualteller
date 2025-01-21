# actualTeller

# Setup
- Create Teller.io developer Account
- If you are using the .env file, change ".env." to ".env" and and fill in the blanks.
- If you are using portainer, change .env to stack.env and input the env data within the Environment Variables -> Advanced Mode link, and paste in the .env contents
- If you are using the docker-compose, fill in your info within that file instead.
- You will have to connect your bank in app. 
- You can perform a manual import first as it will grab all available data.

# Some things worth noting
- You need actual budget accounts in order to link it
- The first initial import does not have a starting balance, you will need to balance it out first.
- The order of the Actual Accounts seems to be the order in which they are created, not the order of the WebGUI. 
- Checking/Savings account work by negating the value received from Teller, so they come up as payments or deposits correctly. If they don't for your use case. Please let me know, the account type may be different than what I'm expecting

# About
This application will connect ActualBudget and Teller.io and uses Actual-HTTP-API in order to use the Actual API. 