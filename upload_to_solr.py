import json
from datetime import datetime

import requests
from pg_python import pg_python as pg_py

# pg_python - database and setup
db_name = 'postgres'
username = 'postgres'
password = 'postgres'
host_address = 'localhost'
table_name = 'ndtv_india'
pgs = pg_py.pg_server(db_name, username, password, host_address)

fields = {
    'id': 'string',
    'title': 'text_general',
    'link': 'text_general',
    'date': 'pdates',
    'author': 'text_general',
    'place': 'text_general',
    'description': 'text_general',
    'content': 'text_general'
}

core = 'ndtv_india'
base_url = "http://localhost:8983/solr"
url = '{}/{}'.format(base_url, core)
headers = {'Content-Type': 'application/json'}

print('Setting schema...')
# setup no auto create fields
no_auto_create = {
    'set-user-property': {
        'update.autoCreateFields': False
    }
}
requests.post('{}/config'.format(url), headers=headers, data=json.dumps(no_auto_create))

# setup fields
for field in fields:
    if field == 'id':
        continue
    payload = {
        'add-field': {
            'name': field,
            'type': fields[field],
            'multiValued': False,
            'stored': True
        }
    }
    resp = json.loads(requests.post('{}/schema'.format(url), headers=headers, data=json.dumps(payload)).text)
    status = resp.get('responseHeader').get('status')
    if status == 400:
        print(resp.get('error').get('details')[0].get('errorMessages')[0].strip())
    elif status == 0:
        print(field, 'ok')
        copy = {
            'add-copy-field': {
                'source': field,
                'dest': '_text_'
            }
        }
        requests.post('{}/schema'.format(url), headers=headers, data=json.dumps(copy))
    else:
        print('Error:\n{}'.format(resp))

print('Schema configured.')

print('importing data...')
data = pg_py.read(table_name, fields.keys(), {'1': '1'})

for record in data:
    rec = record.copy()
    date = datetime.strptime(record['date'], '%Y-%m-%d')
    rec.update({'date': date.isoformat() + 'Z'})
    rec_json = json.dumps({
        'add': {
            'doc': rec,
            'overwrite': True,
            'commitWithin': 1000
        }
    })
    resp = json.loads(requests.post("{}/update?wt=json".format(url), headers=headers, data=rec_json).text)
    if resp.get('responseHeader').get('status') != 0:
        print(resp.get('error').get('msg').strip())

print('imported data.\n{}/#/{}/query'.format(base_url, core))
