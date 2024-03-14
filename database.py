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
                neg INTEGER,
                is_mapped INTEGER
            )
            '''
        )
        self.conn.commit()
    
    def insert_item(self, name, actual_account, teller_account, neg, is_mapped):
        self.cur.execute(
            '''INSERT INTO actual_to_teller
            VALUES (NULL, ?, ?, ?, ?, ?)''',
            (name, actual_account, teller_account, neg, is_mapped))
        self.conn.commit()
    
    def view_items(self):
        self.cur.execute("SELECT * FROM actual_to_teller")
        rows = self.cur.fetchall()
        return rows
    
    def get_accounts_by_name(self,name):
        self.cur.execute("SELECT actual_account, teller_account, neg FROM actual_to_teller WHERE name = ?", (name,))
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
        self.cur.execute("SELECT actual_account, teller_account, neg FROM actual_to_teller WHERE is_mapped = 1")
        accounts = self.cur.fetchall()
        return accounts

    def check_table_data(self):
        self.cur.execute('SELECT COUNT(*) FROM actual_to_teller')
        count =  self.cur.fetchone()[0]
        # print(count)
        # print(count > 0)
        return count > 0

    def reset(self):
        self.cur.execute('DELETE FROM actual_to_teller')
        self.conn.commit()

    def close(self):
        self.conn.close()