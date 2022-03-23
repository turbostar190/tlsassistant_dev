from re import I
import crossplane
from pprint import pprint
import json


payload = crossplane.parse('conf/nginx/nginx.conf', comments=False)
# pprint(payload)
print(json.dumps(payload, indent=2))

# print("---")
# print(payload['config'][0]['parsed'])
# print("---")

# print("---")
# config = crossplane.build(
#     payload['config'][1]['parsed']
# )
# print(config)
# print("---")

# config = crossplane.build(
    # payload['config'][2]['parsed']
# )
# print(config)


# Nella configurazione più base non sono preservati i commenti e gli spazi
# config = crossplane.build(
#     [
#         {
#             "directive": "server",
#             # "line": 1,
#             "args": [],
#             "block": [
#                 {
#                     "directive": "listen",
#                     "args": ['80'],
#                 },
#                 {
#                     "directive": "#",
#                     "comment": "questo è un commento"
#                 },
#                 {
#                     "directive": "prot",
#                     "args": ['a', 'b'],
#                 },
#             ]
#         },
#         {
#             "directive": "user",
#             "args": ['nginx'],
#         },
#     ]         
# )
# print(config)



def structure(payload, struct):
    """
    Funzione ricorsiva per generare una struttura chiave:blocco.

    :param payload: output della libreria parsing nginx
    :type payload: list
    :param struct: modifica la reference a questo dict
    :type struct: dict
    """
    for directive in payload:
        directive_key = directive['directive']
        special = False
        
        if directive_key not in struct:
            struct[directive_key] = []
        # else:
        #     if type(struct[directive_key][0]) == str: # prima volta che scopro che ci sono più chiavi uguali
        #         struct[directive_key] = [struct[directive_key].copy()]
        #     else:
        #         struct[directive_key].append({})
        #         i = len(struct[directive_key])-1
        #         struct[directive_key][i] = directive['args']
        #     special = True

        if 'block' in directive:
            struct[directive_key].append({})
            index = len(struct[directive_key]) - 1

            if len(directive['args']) != 0:
                arg = ' '.join(directive['args']) # Stringa unica per l'argomento di un blocco
                struct[directive_key][index][arg] = {} # Sottoblocco con chiave gli argomenti di un blocco, esempio location >>> = /50x.html <<< {...}
                structure(directive['block'], struct[directive_key][index][arg])
            else:
                structure(directive['block'], struct[directive_key][index])
        # elif not special: 
        else:
            struct[directive_key] = directive['args']

struct = {}
for file in payload['config']:
    # if file['file'] == 'conf/nginx/fastcgi_params':
    struct[file['file']] = {};
    structure(file['parsed'], struct[file['file']])
# pprint(struct)

# struct["conf/nginx/nginx.conf"]['http'][0]['ssl_protocols'].remove('SSLv3')
# pprint(payload)


def rebuild_wrapper(struct: dict, my_payload: list):
    for key, val in struct.items():
        for entry in val:
            my_payload.append({})
            index = len(my_payload) - 1
            my_payload[index]['directive'] = key
            my_payload[index]['args'] = []
            if type(entry) == dict: # sottoblocco incoming
                my_payload[index]['block'] = []
                rebuild(entry, my_payload[index]['block'])
            elif type(entry) == list:
                my_payload[index]['args'] = entry
            else:
                my_payload[index]['args'] = val
                break


def rebuild(struct: dict, my_payload: list):
    for key, val in struct.items():
        if type(val) == list: 
            my_payload.append({})
            index = len(my_payload) - 1

            if len(val) > 0 and type(val[0]) == str: # str degli args
                my_payload[index]['directive'] = key
                my_payload[index]['args'] = val

            else: # primo step sottoblocco
                max = len(val)-1
                for i, v in enumerate(val):
                    my_payload[index]['block'] = []
                    my_payload[index]['directive'] = key
                    my_payload[index]['args'] = list(v.keys()) if type(list(v.values())[0]) == dict else []
                    rebuild(v, my_payload[index]['block'])
                    if i < max:
                        my_payload.append({})
                        index = len(my_payload) - 1

        else: # caso speciale args con sottoblocco: type(val) == dict
            # ogni entry corrisponde ad un nuovo blocco distinto (vedi location)
            for i, (k, v) in enumerate(val.items()):
                my_payload.append({})
                my_payload[i]['directive'] = k
                my_payload[i]['args'] = v


pprint(struct)
for key, val in struct.items():
    my_payload = []
    # rebuild_wrapper(struct['conf/nginx/./conf.d/default.conf'], my_payload)
    # rebuild_wrapper(struct['conf/nginx/nginx.conf'], my_payload)
    # rebuild_wrapper(struct['conf/nginx/fastcgi_params'], my_payload)
    rebuild_wrapper(val, my_payload)

    print("---")
    pprint(my_payload)

    print("---")
    # pprint(payload)
    config = crossplane.build(my_payload)
    print(config)
    




def traverse(payload, http_list, server_list):
    for directive in payload:
        if 'block' in directive:
            if directive['directive'] == 'http':
                http_list.append(directive)
            elif directive['directive'] == 'server':
                server_list.append(directive)
            
            traverse(directive['block'], http_list, server_list)

payload['http'] = []
payload['server'] = []
for file in payload['config']:
    traverse(file['parsed'], payload['http'], payload['server'])

# pprint(payload['http'])
# pprint(payload['server'])
