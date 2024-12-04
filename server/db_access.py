import mysql.connector

class DatabaseConnection:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="130.61.108.82",
            user="u153_qFBOHS3KwU",
            password="!JKT!ibvbbHZfC13=lH@2YgY",
            database="s153_KirilovDB"
        )
        self.cursor = self.connection.cursor()
    
    def query(self, sql_query):
        self.cursor.execute(sql_query)
        if sql_query.startswith("SELECT") or sql_query.startswith("SHOW"):
            return self.cursor.fetchall()
        elif sql_query.startswith("INSERT"):
            self.connection.commit()
            return self.cursor.lastrowid
        elif sql_query.startswith("UPDATE") or sql_query.startswith("DELETE"):
            self.connection.commit()

if __name__ == "__main__":
    db = DatabaseConnection()
    