#!/bin/python3

import requests
import re
import json
import pprint
import yaml
import datetime


jspayload = ''
if not os.path.exists('apidoc.js'):
    url_to_parse = "https://pve.proxmox.com/pve-docs/api-viewer/apidoc.js"
    jspayload = requests.get(url_to_parse).text
else:
    jspayload = open('apidoc.js').read()

search = re.search(r'(?<=var pveapi =)[\s\S]*?(?=;\n)', jspayload, re.MULTILINE)

if not search:
    raise Exception("failed to find api doc definition")

data = json.loads(search.group())

todo = []

todecoded = data[:]

# flatten the api tree
while todecoded:
    item = todecoded.pop()
    
    if item['leaf'] != 1:
        todecoded.extend(item['children'])
        del item['children']
    todo.append(item)

paths = {}


def convertReturns(returns):
    if not returns:
        return

    returnType = returns.get('type')

    if not returnType:
        pass



def convertParameters(method, path, parameters):
    if not parameters or not parameters.get('properties'):
        return [], {}

    ret = []
    bodyParameters = {}

    for name, definition in parameters['properties'].items():
        shouldGoToBody = False
        param = {
            'name': name,
            'schema': {
                'type': definition['type'],
            },
        }
        if definition.get('optional', 0) != 1:
            param['required'] = True

        if 'description' in definition:
            param['description'] = definition['description']

        if f'{{{name}}}' in path:
            param['in'] = 'path'
        else:
            if method not in ['POST', 'PUT']:
                param['in'] = 'query'
            else:
                bodyParameters[name] = definition
                continue

        if 'format' in definition:
            param['schema']['format'] = definition['format']
        
        if 'default' in definition:
            param['schema']['default'] = definition['default']
        ret.append(param)

    return ret, bodyParameters

for item in todo:
    methods = {}
    for method, payload in item.get('info', {}).items():
        parameters, bodyParameters = convertParameters(method, item['path'], payload['parameters'])

        methods[method.lower()] = {
            "summary": payload['description'],
            "parameters": parameters,
            "responses": {
                '200': convertReturns(payload['returns'])
            }
        }
        if bodyParameters:
            methods[method.lower()]['requestBody'] = {
                'content': {
                    "application/x-www-form-urlencoded": {
                        'schema': {
                            'type': 'object',
                            'properties': bodyParameters
                        },
                        'required': [i for i, j in bodyParameters.items() if j.get('optional', 0) != 1]
                    }
                }
            }
    paths[item['path']] = methods

with open('openapi.yaml', 'w') as fp:
    fp.write(yaml.dump({
        'openapi': '3.0.0',
        'info': {
            'title': 'Proxmox API',
            'version': datetime.datetime.now().strftime('%Y%m%d'),
        },
        'externalDocs': {
            'description': 'Official API Viewer',
            'url': 'https://pve.proxmox.com/pve-docs/api-viewer/'
        },
        'paths': paths
    }))