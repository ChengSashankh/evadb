# Import the EvaDB package
import evadb
import pandas as pd

# Connect to EvaDB and get a database cursor for running queries
cursor = evadb.connect().cursor()
#
# # List all the built-in functions in EvaDB
# print(cursor.query("""
# CREATE DATABASE IF NOT EXISTS reddit_data WITH ENGINE = 'reddit', PARAMETERS = {
#         "subreddit": "AskReddit",
#         "client_id": "0SrFH3UpNSwPXKHlYJn77g",
#         "clientSecret": "9GEiJwOAmAgshLcY9-4rQRMXaR-oig",
#         "userAgent": "Eva DB Staging Build"
#    };
# """).df())
#
# df = cursor.query("""
# SELECT author, title, url FROM reddit_data.submissions LIMIT 10;
# """).df()
#
# print(df.head(n=10))

df = cursor.query("SELECT ChatGPT()")



# print(cursor.query("""
# CREATE DATABASE github_data WITH ENGINE = 'github', PARAMETERS = {
#         "owner": "georgia-tech-db",
#         "repo": "evadb"
#    };
# """).df())
