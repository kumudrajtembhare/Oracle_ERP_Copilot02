import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
import pyodbc
import time
import asyncio
import pandas as pd
import streamlit as st
import cx_Oracle  
import configparser
import requests
from bs4 import BeautifulSoup

# Native functions are used to call the native skills
# 1. Create speech from the text
# 2. Create text from user's voice through microphone

# Semantic functions are used to call the semantic skills
# 1. nlp_sql: Create SQL quer


#st.title('Oracle Copilot')
st.markdown("<h3> Oracle Copilot</h3>", unsafe_allow_html=True) 
# Display an image using Streamlit
img_path = "readme_assets\oracle.png"  # Replace with your image path
st.image(img_path, caption='Your Chatbot', use_column_width=False, width=200,output_format='auto')
    # Set the path to the Oracle Instant Client  
cx_path = r'instantclient_19_24' 

    #C:\Users\Documents\instantclient-basic-windows.x64-21.7.0.0.0dbru\instantclient_21_7
  
    # Initialize the Oracle client  
print (cx_Oracle.version)
try:
    cx_Oracle.init_oracle_client(lib_dir=cx_path)
except Exception as err:
    print("Error connecting: cx_Oracle.init_oracle_client()")
    print(err);

# Web scraping function to get table and column info from the website
def scrape_table_info():
    url = "https://etrm.live/etrm-12.2.2/etrm.oracle.com/pls/trm1222/etrm_pnav7eb4-3.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    table_info = {}
    
    # Find and parse the table and column information (this depends on the page structure)
    # Here, adjust the parsing logic to match the HTML structure of the target page
    for table in soup.find_all("table", class_="table-class"):  # Example class name
        table_name = table.find("oe_order_headers_all").text.strip()  # Assuming table name is in an h3 tag
        columns = [col.text.strip() for col in table.find_all("td", class_="column-class")]  # Example column class name
        table_info[table_name] = columns
    
    return table_info

# Function to integrate table info into SQL generation
def integrate_table_info(prompt, table_info):
    for table, columns in table_info.items():
        if table in prompt:
            prompt += f" Use the table {table} with columns {', '.join(columns)}."
            break
    return prompt




def semanticFunctions(kernel, skills_directory, skill_name, input):
    functions = kernel.import_semantic_skill_from_directory(skills_directory, "plugins")
    summarizeFunction = functions[skill_name]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = summarizeFunction(input)
    finally:
        loop.close()
    return result

# Function to call the Oracle procedure to insert feedback into the database
def insert_feedback_to_db(user_question, sql_query, data_output, feedback, good_response_flag, bad_response_flag):
    # Connection details  
    hostname = os.environ.get("server_name")
    username = os.environ.get("SQLADMIN_USER")
    password = os.environ.get("SQL_PASSWORD")
    port_number_oracle = os.environ.get("port_no")
    service_name_oracle = os.environ.get("database_name")

    try:
        # Connect to the Oracle database  
        conn = cx_Oracle.connect(
            username,  
            password,  
            f"{hostname}:{port_number_oracle}/{service_name_oracle}",  
            encoding="UTF-8"  
        )
        
        # Create a cursor and call the stored procedure  
        cursor = conn.cursor()
        try:
            cursor.callproc("XXNUAN.INSERT_COPILOT_FEEDBACK", [
                user_question,
                sql_query,
                data_output,
                feedback,
                good_response_flag,
                bad_response_flag
            ])
            conn.commit()  # Commit the transaction
            cursor.close()
            conn.close()
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            st.error(f"Database error: {error.message}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")

# Function to get the result from the database
def get_result_from_database(sql_query):
    # Connection details  
    hostname = os.environ.get("server_name")
    username = os.environ.get("SQLADMIN_USER")
    password = os.environ.get("SQL_PASSWORD")
    port_number_oracle = os.environ.get("port_no")
    service_name_oracle = os.environ.get("database_name") 
    
    try:
        # Connect to the Oracle database  
        conn = cx_Oracle.connect(
            username,  
            password,  
            f"{hostname}:{port_number_oracle}/{service_name_oracle}",  
            encoding="UTF-8"  
        )  
      
        # Create a cursor and execute a query  
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            conn.close()

            # If the result is empty, return a specific message
            if not result:
                return {"error": "No results were found for your query."}
            
            # Convert the result to a DataFrame
            data = [dict(zip(columns, row)) for row in result]
            df = pd.DataFrame(data)
            return df

        except cx_Oracle.DatabaseError as e:
            error, = e.args
            if "ORA-00933" in error.message:
                return {"error": "Database error: ORA-00933: SQL command not properly ended. Please check the syntax of your query."}
            return {"error": f"Database error: {error.message}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Function to check if the new question is related to the previous context
def is_related_question(new_question, context):
    context_keywords = set(context.split()) if context else set()
    new_question_keywords = set(new_question.split())
    
    # Calculate keyword overlap
    common_keywords = context_keywords.intersection(new_question_keywords)
    
    # If there are common keywords, consider it a related question
    return len(common_keywords) > 0

def main():

    #Load environment variables from .env file
    load_dotenv()

    # Scrape the table and column information
    table_info = scrape_table_info()

    kernel = sk.Kernel()

    # Configure AI service used by the kernel
    deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()

    # Add the AI service to the kernel
    kernel.add_text_completion_service("dv", AzureChatCompletion(deployment_name=deployment, endpoint=endpoint, api_key=api_key))

    # Initialize session state for context management
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.context = ""

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message.get("role")):
            st.write(message.get("content"))

    # Get the user input
    prompt = st.chat_input("Ask Something")

    # Initialize result variable to avoid UnboundLocalError
    result = None

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Check if the new question is related to the previous context
        if st.session_state.context and not is_related_question(prompt, st.session_state.context):
            st.session_state.context = ""  # Reset context if the question is unrelated

        # Update context if needed
        if st.session_state.context:
            prompt = f"{st.session_state.context} {prompt}"

        # Integrate table information into the prompt
        prompt = integrate_table_info(prompt, table_info)

        # Generate SQL query from the prompt
        skills_directory = "."
        sql_query = semanticFunctions(kernel, skills_directory, "nlpToSQLPlugin", prompt)
        sql_query = sql_query.result.split(';')[0]
        st.session_state.messages.append({"role":"assistant","content":sql_query})
        with st.chat_message("Assistant"):
            st.write(sql_query)

        # Get the result from the database
        result = get_result_from_database(sql_query)

    # Check if the result contains an error or if the query was executed
    if result is not None:
        if isinstance(result, dict) and "error" in result:
            st.session_state.messages.append({"role":"error","content":result["error"]})
            with st.chat_message("error"):
                st.error(result["error"])
            # Insert feedback with bad response flag
            insert_feedback_to_db(prompt, sql_query, None, "No results", "N", "Y")            
        elif isinstance(result, pd.DataFrame) and not result.empty:  # Explicitly check if DataFrame is not empty
            st.session_state.messages.append({"role":"answer","content":result})
            with st.chat_message("answer"):
                st.table(result)
            # Insert feedback with good response flag
            insert_feedback_to_db(prompt, sql_query, result.to_json(), "Good result", "Y", "N")
        else:
            standard_message = "The query did not find data, kindly modify your request."
            st.session_state.messages.append({"role":"answer","content":standard_message})
            with st.chat_message("answer"):
                st.write(standard_message)
            # Insert feedback with bad response flag
            insert_feedback_to_db(prompt, sql_query, None, standard_message, "N", "Y")

        # Update the context for follow-up questions
        st.session_state.context = prompt


if __name__ == "__main__":
    start = time.time()
    main()
    print("Time taken Overall(mins): ", (time.time() - start)/60)