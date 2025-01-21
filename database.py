import sqlite3

class Database():
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cur = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS actual_to_teller (
                id INTEGER PRIMARY KEY,
                name TEXT,
                actual_account TEXT,
                teller_account TEXT,
                is_mapped INTEGER
            );
            '''
        )        
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS bank_tokens (
                id INTEGER PRIMARY KEY,
                name TEXT,
                token TEXT
            );            
            '''
        )
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS token_accounts (
               id INTEGER PRIMARY KEY,
               token TEXT,
               account TEXT,
               name TEXT,
               account_type TEXT,
               enrollment_id TEXT,
               FOREIGN KEY (token) REFERENCES bank_tokens(token)
            );
            '''
        )
        self.conn.commit()
    
    def insert_item(self, name, actual_account, teller_account, is_mapped):
        self.cur.execute(
            ''' UPDATE actual_to_teller SET name=?, actual_account=?, teller_account=?, is_mapped=?
            WHERE actual_account=?
            ''',(name, actual_account, teller_account, is_mapped, actual_account))
        if self.cur.rowcount == 0:
            self.cur.execute(
                '''INSERT INTO actual_to_teller
                VALUES (NULL, ?, ?, ?, ?)''',
                (name, actual_account, teller_account, is_mapped))
        self.conn.commit()

    def insert_token(self, name, token):
        self.cur.execute(
            '''INSERT INTO bank_tokens
            VALUES (NULL, ?, ?)''',
            (name, token))
        self.conn.commit()

    def insert_account(self, token, account, name_last_four, account_type, enrollment_id):
        self.cur.execute(
            '''INSERT INTO token_accounts
            VALUES (NULL, ?, ?, ?, ?, ?)''',
            (token, account, name_last_four, account_type, enrollment_id))
        self.conn.commit()
    
    def view_items(self):
        self.cur.execute("SELECT * FROM actual_to_teller")
        rows = self.cur.fetchall()
        return rows

    def view_tokens(self):
        self.cur.execute("SELECT * FROM bank_tokens")
        rows = self.cur.fetchall()
        return rows
    
    def get_accounts_by_name(self, name):
        self.cur.execute('''
            SELECT 
                att.actual_account, 
                att.teller_account,
                ta.account_type
            FROM 
                actual_to_teller AS att
            JOIN
                token_accounts AS ta
            ON
                att.teller_account = ta.account
            WHERE 
                att.name = ?
        ''', (name,))
        accounts = self.cur.fetchall()
        return accounts[0]

    def get_linked_accounts_names(self):
        self.cur.execute("SELECT name FROM actual_to_teller WHERE is_mapped = 1")
        mapped_rows = [row[0] for row in self.cur.fetchall()]
        return mapped_rows
    
    def get_unlinked_accounts_names(self):
        self.cur.execute("SELECT name FROM actual_to_teller WHERE is_mapped = 0")
        mapped_rows = [row[0] for row in self.cur.fetchall()]
        return mapped_rows
    
    def get_all_linked_accounts(self):
        self.cur.execute('''
            SELECT 
                att.name,
                att.actual_account, 
                att.teller_account,
                ta.account_type
            FROM 
                actual_to_teller AS att
            JOIN
                token_accounts AS ta
            ON
                att.teller_account = ta.account
            WHERE
                att.is_mapped = 1
        ''')
        accounts = self.cur.fetchall()
        return accounts

    def get_accounts_for_reset(self):
        self.cur.execute('''
            SELECT 
                att.actual_account,
                att.teller_account
            FROM 
                actual_to_teller AS att
            JOIN
                token_accounts AS ta
            ON
                att.teller_account = ta.account
            WHERE
                att.is_mapped = 1
        ''')
        accounts = self.cur.fetchall()
        return accounts

    def get_all_token_accounts(self):
        self.cur.execute("SELECT token, account, name, account_type, enrollment_id FROM token_accounts")
        token_account_name = self.cur.fetchall()
        return token_account_name
    
    def check_token_accounts(self):
        self.cur.execute('SELECT COUNT(*) FROM token_accounts')
        number_of_accounts = self.cur.fetchone()[0]
        return number_of_accounts

    def check_table_data(self):
        self.cur.execute('SELECT COUNT(*) FROM actual_to_teller WHERE is_mapped = 1')
        count = self.cur.fetchone()[0]
        return count > 0
    
    def get_token_from_account_id(self, account):
        self.cur.execute('SELECT token FROM token_accounts WHERE account = ?', (account,))
        token = self.cur.fetchone()
        return token[0]
    
    def get_actual_name_from_teller_accounts(self):
        self.cur.execute('''
            SELECT 
                att.name AS actual_name,
                ta.enrollment_id   
            FROM
                actual_to_teller AS att
            JOIN
                token_accounts AS ta
            ON 
                att.teller_account = ta.account
        ''')
        results = self.cur.fetchall()
        return results

    def reset(self):
        self.cur.execute('UPDATE actual_to_teller SET teller_account = NULL, is_mapped = NULL')
        self.conn.commit()

    def close(self):
        self.conn.close()