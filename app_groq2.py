import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

GROQ_API_KEY = "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"

def connectDatabase(username, password, host, port, database):
    mysql_uri = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
    st.session_state.db = SQLDatabase.from_uri(mysql_uri)
    
def runQuery(query):
    return st.session_state.db.run(query) if st.session_state.db else "Database not connected."

def getDatabaseSchema():
    return st.session_state.db.get_table_info() if st.session_state.db else "Database not connected."

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile",
)

def getQueryFromLLM(question):
    template = """
    You are an SQL generator. Output ONLY a valid SQL query.

    1. Use ONLY columns from schema below. NEVER invent new columns (e.g., do NOT use 'menu').
    2. NEVER use JOIN unless the table exists in the schema.
    - If the schema contains only the restaurants table, never write JOIN.
    - 'daerah' is a column, not a table.
    3. For food categories (pizza, asia, barbekyu, seafood, dll), ALWAYS filter with:
    tipe_makanan LIKE '%<value>%'
    4. For location filtering (Lombok, Mataram, Gili, Senggigi), ALWAYS filter with:
    daerah LIKE '%<value>%'
    5. For rating comparison (e.g., di atas 4), ALWAYS use:
    CAST(rating AS DECIMAL(4,2)) > <value>
    6. If the user requests a number (e.g., 3 restoran), ALWAYS use:
    LIMIT <number>
    7. Output SQL only — no explanation. No ```.

    Schema:
    {schema}

    User Question: {question}

    SQL:
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "schema": getDatabaseSchema()        
    })
    return response.content.strip()

def getResponseForQueryResult(question, query, result):
    template2 = """
    Convert SQL query result into a natural language answer.

    STRICT RULES:
    1. Always list ALL restaurants from the SQL result.
    2. If the result list is empty, say that no data was found.
    3. Do NOT add information that does not exist in the result.
    4. explain the restaurant details based on the result.
    5. Use the same language as the user.
    6. Do NOT repeat the SQL query.
    7. If the result of price explain $ sign as cheap, $$ as medium, $$$ as expensive.

    Schema:
    {schema}

    User Question: {question}

    SQL Result (Python list): {result}

    Answer:
    """

    prompt2 = ChatPromptTemplate.from_template(template2)
    chain2 = prompt2 | llm

    response = chain2.invoke({
        "question": question,
        "schema": getDatabaseSchema(),
        "result": result
    })
    return response.content.strip()

st.title("💬 Chatbot SQL: Tanya Data Restoran 🍽️")
st.set_page_config(
    page_title="SQL Agent with Llama3.2", 
    page_icon=":robot:",
    layout="centered",
)

question = st.chat_input('Chat with your Assistant')

if "chat" not in st.session_state:
    st.session_state.chat = []
    
if question:
    if "db" not in st.session_state:
        st.error("Please connect to the database first.")
    else:
        st.session_state.chat.append({
            "role": "user", 
            "content": question
        })        
        query = getQueryFromLLM(question).strip().replace("```", "")
        print("Generated Query:", query)
        result = runQuery(query)
        print("Query Result:", result)
        response = getResponseForQueryResult(question, query, result)
        st.session_state.chat.append({
            "role": "assistant", 
            "content": response
        })    
        
for chat in st.session_state.chat:
    st.chat_message(chat["role"]).markdown(chat["content"])
    
with st.sidebar:
    st.title("Connect To Database")
    st.text_input(label="Host", key="host", value="localhost")
    st.text_input(label="Port", key="port", value="3306")
    st.text_input(label="Username", key="username", value="root")
    st.text_input(label="Password", key="password", value="", type="password")
    st.text_input(label="Database", key="database", value="rag")
    connectBtn = st.button("Connect")
    
if connectBtn:
    connectDatabase(
        username=st.session_state.username,
        password=st.session_state.password,
        host=st.session_state.host,
        port=st.session_state.port,
        database=st.session_state.database
    )
    
    print(getDatabaseSchema())
    st.success("Connected to Database")