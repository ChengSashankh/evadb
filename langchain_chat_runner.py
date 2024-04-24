import evadb
from gptcache.adapter.openai import cache_openai_chat_complete

cursor = evadb.connect().cursor()
print(cursor.query("SHOW FUNCTIONS;").df())

cursor.query("DROP FUNCTION IF EXISTS ChatGPTWithLangchain").df()

cursor.query("""
CREATE FUNCTION ChatGPTWithLangchain
IMPL 'evadb/functions/chatgpt_langchain.py'
model 'gpt-3.5-turbo';
""").df()

# print(cursor.query("SHOW FUNCTIONS;").df())
#
# print(cursor.query("CREATE TABLE IF NOT EXISTS TestTable2 (id TEXT);").df())
#
# print(cursor.query("INSERT INTO TestTable2 (id) VALUE ('Who is Sachin Tendulkar?'), ('Tell me about Sachin Tendulkar?')").df())
#
# print(cursor.query("SELECT * FROM TestTable2").df())

no_cache_chatgpt_udf = """
    SELECT ChatGPTWithLangchain('About what sport is the question given below? Answer in 1 word only. Sport:', id, 'You are a helpful assistant whose job is it to answer the questions you are asked.', TRUE)
    FROM TestTable2;
"""
cache_chatgpt_udf = """
    SELECT ChatGPTWithLangchain('About what sport is the question given below? Answer in 1 word only. Sport:', id, 'You are a helpful assistant whose job is it to answer the questions you are asked.', FALSE)
    FROM TestTable2;
"""
from time import time

latencies = []

start_time = time()
print(cursor.query(no_cache_chatgpt_udf).df())
end_time = time()
latencies.append(end_time - start_time)

print (latencies)

latencies = []

start_time = time()
print(cursor.query(cache_chatgpt_udf).df())
end_time = time()
latencies.append(end_time - start_time)

print (latencies)
# from openai import OpenAI
# from gptcache import cache
#
#
#
# args = {'model': 'gpt-3.5-turbo', 'temperature': 0,
#         'messages': [{'role': 'system', 'content': 'You are a helpful assistant that accomplishes user tasks.'},
#                      {'role': 'user', 'content': 'Here is some context : Who is Sachin Tendulkar?'}, {'role': 'user',
#                                                                                                       'content': 'Complete the following task: Is this video summary related to Ukraine russia war?'}]}
#
# for _ in range(3):
#     cache.init()
#     client = OpenAI()
#     cache_openai_chat_complete(client=client, **args)
