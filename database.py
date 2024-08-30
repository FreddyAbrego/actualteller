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
                is_neg INTEGER,
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
        self.conn.commit()
    
    def insert_item(self, name, actual_account, teller_account, is_neg, is_mapped):
        self.cur.execute(
            ''' UPDATE actual_to_teller SET name=?, actual_account=?, teller_account=?, is_neg=?, is_mapped=?
            WHERE name=?
            ''',(name, actual_account, teller_account, is_neg, is_mapped, name))
        if self.cur.rowcount == 0:
            self.cur.execute(
                '''INSERT INTO actual_to_teller
                VALUES (NULL, ?, ?, ?, ?, ?)''',
                (name, actual_account, teller_account, is_neg, is_mapped))
        self.conn.commit()

    def insert_token(self, name, token):
        self.cur.execute(
            '''INSERT INTO bank_tokens
            VALUES (NULL, ?, ?)''',
            (name, token))
        self.conn.commit()
    
    def view_items(self):
        self.cur.execute("SELECT * FROM actual_to_teller")
        rows = self.cur.fetchall()
        return rows

    def view_tokens(self):
        self.cur.execute("SELECT * FROM bank_tokens")
        rows = self.cur.fetchall()
        return rows
    
    def get_accounts_by_name(self,name):
        self.cur.execute("SELECT actual_account, teller_account, is_neg FROM actual_to_teller WHERE name = ?", (name,))
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
        self.cur.execute("SELECT name, actual_account, teller_account, is_neg FROM actual_to_teller WHERE is_mapped = 1")
        accounts = self.cur.fetchall()
        return accounts

    def check_table_data(self):
        self.cur.execute('SELECT COUNT(*) FROM actual_to_teller WHERE is_mapped = 1')
        count =  self.cur.fetchone()[0]
        # print(count)
        # print(count > 0)
        return count > 0

    def get_negative_rows(self):
        self.cur.execute('SELECT name FROM actual_to_teller WHERE is_neg = 1')
        negative_rows = [row[0] for row in self.cur.fetchall()]
        # print(f'negative rows: {negative_rows}')
        return negative_rows

    def reset(self):
        self.cur.execute('UPDATE actual_to_teller SET teller_account = NULL, is_mapped = NULL')
        self.conn.commit()

    def close(self):
        self.conn.close()