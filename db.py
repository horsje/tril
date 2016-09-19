import pyodbc


class DB:
    def __init__(self, file):
        self.conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + file)

    def update(self, query, params):
        cursor = self.conn.cursor().execute(query, params)
        self.conn.commit()
        return cursor.rowcount

    def query(self, query, params=None):
        if params:
            cursor = self.conn.cursor().execute(query, params)
        else:
            cursor = self.conn.cursor().execute(query)
        columns = [column[0] for column in cursor.description]
        result = []
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        return result
