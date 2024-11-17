import psycopg2
from psycopg2 import sql

connection = psycopg2.connect(
    user='superset', 
    password='superset',
    host='172.25.0.18',
    port='5432', 
    database='superset'
)
cursor = connection.cursor()
try:
    connection.autocommit = True
    cursor.execute(sql.SQL('CREATE DATABASE sales_db'))
    print('sales_db database created in PostgreSQL')
except psycopg2.errors.DuplicateDatabase:
    print('Database sales_db already exists')
finally:
    connection.autocommit = False
connection.close()

conn = psycopg2.connect(
    user='superset',  
    password='superset',
    host='172.25.0.18',
    port='5432',  
    database='sales_db'
)

cur = conn.cursor()

SQL = """
CREATE TABLE IF NOT EXISTS sales(
    Sale_ID INT,
    Product VARCHAR(40),
    Quantity_Sold INT,
    Each_Price FLOAT,
    Sales FLOAT,
    Date DATE,
    Day INT,
    Month INT,
    Year INT
)
"""
cur.execute(SQL)
print('sales table created')

SQL = """
CREATE TABLE IF NOT EXISTS stocks(
    Product VARCHAR(40),
    Stock_Quantity INT,
    Total_Quantity_Sold INT
)
"""
cur.execute(SQL)
print('stocks table created')

conn.commit()
conn.close()
print("done!")
