import os
import cx_Oracle  
import configparser    
import pandas as pd
import os
import platform
import sys 
# This is the path to the ORACLE client files
cx_path = r"C:\Users\rbhaskaran\Downloads\App-main\TestApp\nlp-sql-in-a-box_Oracle\instantclient_19_24"
try:
    cx_Oracle.init_oracle_client(lib_dir=cx_path)
except Exception as err:
    print("Error connecting: cx_Oracle.init_oracle_client()")
    print(err);
    sys.exit(1);


# Test to see if the cx_Oracle is recognized
print(cx_Oracle.version)   # this returns 8.0.1 for me

# This fails for me at this point but will succeed after the solution described below
cx_Oracle.clientversion()  
  
# Connection details  
hostname = "eusr12qadb01.nuance.com" #os.environ.get("server_name")
#database_name = os.environ.get("database_name")
username = "apps"
password = "Qt2ebzF3_n3mo"
port_number_oracle = 1531 
service_name_oracle = "LR12QA1"
#replace your credentials above
try:  
        # Connect to thecx_Oracle.conn
        connection = cx_Oracle.connect(
            username,  
            password,  
            f"{hostname}:{port_number_oracle}/{service_name_oracle}",  
            encoding="UTF-8"  
        )  
      
        # Create a cursor and execute a query  
        cursor = connection.cursor()  
        cursor.execute("SELECT sysdate FROM dual") 
        
        # Fetch the query results  
        output = cursor.fetchall()  
        print(output)  
  
except Exception as e:  
        print('Oracle connection failed:', e)
    
