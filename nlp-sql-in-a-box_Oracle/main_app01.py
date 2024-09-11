import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
#from plugins.ttsPlugin.ttsPlugin import TTSPlugin
#from plugins.sttPlugin.sttPlugin import STTPlugin
from dotenv import load_dotenv
import pyodbc
import time
import asyncio
import pandas as pd
import streamlit as st
import cx_Oracle  
import configparser
import sys

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


def main():

    #Load environment variables from .env file
    load_dotenv()

    # Create a new kernel
    kernel = sk.Kernel()
    #context = kernel.create_new_context()
    #context['result'] = ""

    # Configure AI service used by the kernel
    deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()

    # Add the AI service to the kernel
    kernel.add_text_completion_service("dv", AzureChatCompletion(deployment_name=deployment, endpoint=endpoint, api_key=api_key))

    # Starting the Conversation
    #speak_out_response(kernel,context,"....Welcome to the Kiosk Bot!! I am here to help you with your queries. I am still learning. So, please bear with me.")
    #repeat = True
    #while(repeat):
        #speak_out_response(kernel,context,"Please ask your query through the Microphone:")
        #print("Listening:")

        # Taking Input from the user through the Microphone
        #query = recognize_from_microphone(kernel, context)
        #print("Processing........")
        #print("The query is: {}".format(query))
        
        # Processing the query
        # Generating summary
        #st.write('Hey, Hi')
        #st.chat_input(key="chat_input_1")
    #create storage message
    if "messages"   not in  st.session_state:
        st.session_state.messages=[]
    
    #display  chat history
    #st.write(st.session_state.messages)
    for message in st.session_state.messages:
        with st.chat_message(message.get("role")):
            st.write(message.get("content"))
    prompt = st.chat_input("Ask Something")
    
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            query = st.write(prompt)

    # Generate SQL query from the prompt
    skills_directory = "."
    sql_query = semanticFunctions(kernel, skills_directory, "nlpToSQLPlugin", prompt)
    sql_query = sql_query.result.split(';')[0]
    st.session_state.messages.append({"role":"assistant","content":sql_query})
    with st.chat_message("Assistant"):
        st.write(sql_query)
   
    # Execute the SQL query and get the result
    result = get_result_from_database(sql_query)

    # Check if the result contains an error
    if isinstance(result, dict) and "error" in result:
        st.session_state.messages.append({"role":"error","content":result["error"]})
        with st.chat_message("error"):
            st.error(result["error"])
    else:
        st.session_state.messages.append({"role":"answer","content":result})
        with st.chat_message("answer"):
            st.table(result)

if __name__ == "__main__":
    start = time.time()
    main()
    print("Time taken Overall(mins): ", (time.time() - start)/60)

