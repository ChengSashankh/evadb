import evadb
import pandas as pd
import numpy as np
from time import time

cursor = evadb.connect().cursor()
print(cursor.query("SHOW FUNCTIONS;").df())
print(cursor.query("CREATE TABLE IF NOT EXISTS ques_keys(question TEXT, keys TEXT)").df())
print(cursor.query(f"LOAD CSV 'questions_keys.csv' INTO ques_keys").df())
print(cursor.query("SHOW TABLES;").df())


def create_user_defined_function(cursor):
    cursor.query("DROP FUNCTION IF EXISTS ChatGPTWithLangchain").df()

    cursor.query("""
    CREATE FUNCTION ChatGPTWithLangchain
    IMPL 'evadb/functions/chatgpt_langchain.py'
    model 'gpt-3.5-turbo';
    """).df()


# TODO: Not in use, done directly through sqlite
def load_data_into_table(csv_file_path: str, table_name: str):
    df = pd.read_csv(csv_file_path)
    print(df.head())


def view_data(table_name: str):
    print(cursor.query(f"SELECT * FROM {table_name} LIMIT 3;").df())


def get_chatgpt_query_without_cache():
    no_cache_chatgpt_udf = f"""
        SELECT ChatGPTWithLangchain('About what subject is the question given below. Your answer must be one of Chemistry, Computer Science (cs), Geography, Math, Physics. \n Answer in one word only. \n Subject:', question, 'You are a helpful assistant whose job it is to answer the questions you are asked.', TRUE)
        FROM ques_keys LIMIT 50;
    """

    return no_cache_chatgpt_udf


def get_chatgpt_query_with_cache():
    cache_chatgpt_udf = f"""
        SELECT ChatGPTWithLangchain('About what subject is the question given below. Your answer must be one of Chemistry, Computer Science (cs), Geography, Math, Physics. \n Answer in one word only. \n Subject:', question, 'You are a helpful assistant whose job it is to answer the questions you are asked.', FALSE)
        FROM ques_keys LIMIT 50;
    """

    return cache_chatgpt_udf


def benchmark(with_cache):
    if with_cache:
        query = get_chatgpt_query_with_cache()
    else:
        query = get_chatgpt_query_without_cache()

    start_time = time()
    results_df = cursor.query(query).df()
    end_time = time()
    latency = end_time - start_time

    print(f"Latency with cache={with_cache}: {latency}")

    return latency, results_df


def get_accuracy(correct_ans, results_cache, results_nocache):
    print(correct_ans)
    print(results_cache['response'])
    print(results_nocache['response'])
    print(correct_ans == results_nocache['response'].reset_index(drop=True))
    accuracy_nocache = np.mean(correct_ans == results_nocache['response'].reset_index(drop=True).map(lambda x: x.lower()))
    accuracy_cache = np.mean(correct_ans == results_cache['response'].reset_index(drop=True).map(lambda x: x.lower()))

    return accuracy_cache, accuracy_nocache


correct_ans = pd.read_csv('questions_keys.csv').iloc[:50]['keys'].map(lambda x: x.lower())
latency_cache, results_cache = benchmark(True)
latency_nocache, results_nocache = benchmark(False)

acc_cache, acc_nocache = get_accuracy(correct_ans, results_cache, results_nocache)
print(f"""
    No cache: accuracy = {acc_nocache * 100.0}%, latency = {latency_nocache} \n
    Cache:    accuracy = {acc_cache * 100.0}%, latency = {latency_cache} \n
    """)
