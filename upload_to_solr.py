import json

import requests
from pg_python import pg_python as pg_py

# pg_python - database and setup
db_name = 'postgres'
username = 'postgres'
password = 'postgres'
host_address = 'localhost'
table_name = 'ndtv_india2'
pgs = pg_py.pg_server(db_name, username, password, host_address)

data = pg_py.read(table_name, ['title', 'link', 'date', 'author', 'place', 'description', 'content'], {'1': '1'})
for record in data:
    rec_json = json.dumps(record)
    if not rec_json:
        continue
    requests.post("http://localhost:8983/solr/ndtv_india/update?wt=json", headers={"Content-Type": "application/json"},
                  data='{"add":{ "doc":' + rec_json + ',"overwrite":true, "commitWithin": 1000}}')
