import crossplane
from pprint import pprint
import json
import ast


payload = crossplane.parse('conf/nginx/nginx_.conf', comments=False)
# pprint(payload)
print(json.dumps(payload, indent=2))

# print("---")
# print(payload['config'][0]['parsed'])
# print("---")

# print("---")
# config = crossplane.build(
    # payload['config'][0]['parsed']
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
        elif 'block' not in directive: 
            # se esiste già questa chiave ma non è un inizio di sottoblocco,
            # allora è una lista di lista, ad indicare più direttive con uguale chiave
            # ma distinto valore.
            # Esempio: 
            # {
            #   listen 80;
            #   listen 443 ssl;
            # }
            # diventa
            #   {'listen': [['80'], ['443', 'ssl']]}
            if any(isinstance(el, str) for el in struct[directive_key]):
                # prima volta che scopro che ci sono più chiavi uguali,
                # quindi modifico il valore della chiave in array, e aggiungo 
                # ciò che ho attualmente nel loop...
                struct[directive_key] = [struct[directive_key], directive['args']]
                special = True
            elif any(isinstance(el, list) for el in struct[directive_key]):
                struct[directive_key].append(directive['args'])
                special = True

        if 'block' in directive:
            struct[directive_key].append({})
            index = len(struct[directive_key]) - 1

            if len(directive['args']) != 0:
                arg = repr(directive['args']) # repr della lista per argomento di un blocco
                struct[directive_key][index][arg] = {} # Sottoblocco con chiave gli argomenti di un blocco, esempio location >>> = /50x.html <<< {...}
                structure(directive['block'], struct[directive_key][index][arg])
            else:
                structure(directive['block'], struct[directive_key][index])
        elif not special: # se non è un inizio di sottoblocco e non è già stato elaborato in precedenza
            struct[directive_key] = directive['args']

struct = {}
for file in payload['config']:
    struct[file['file']] = {};
    structure(file['parsed'], struct[file['file']])
# pprint(struct)
print(json.dumps(struct, indent=2))

# struct["conf/nginx/nginx.conf"]['http'][0]['ssl_protocols'].remove('SSLv3')
# pprint(payload)


def rebuild_wrapper(struct, my_payload):
    """
    Funzione wrapper per ritornare alla struttura della libreria 'crossplane' 
    dalla struttura personalizzata.

    :param struct: struttura dati custom creata dalla funzione `structure`
    :type struct: dict
    :param my_payload: output con modifica della reference a questa list
    :type my_payload: list
    """
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


def rebuild(struct, my_payload):
    """
    Funzione ricorsiva per generare struttura dati utilizzata dalla libreria `crossplane`
    dalla nostra struttura custom
    
    :param struct: struttura dati custom creata dalla funzione `structure`
    :type struct: dict
    :param my_payload: output con modifica della reference a questa list
    :type my_payload: list
    """
    for key, val in struct.items():
        if type(val) == list:
            my_payload.append({})
            index = len(my_payload) - 1

            if len(val) > 0 and type(val[0]) == str: # str degli args
                my_payload[index]['directive'] = key
                my_payload[index]['args'] = val
            else: # primo inizio di sottoblocco
                max = len(val) - 1
                for cont, v in enumerate(val):
                    if type(v) == list:
                        # Caso nel cui fosse una lista di liste come direttive multiple con stessa chiave e valori diversi
                        if len(v) > 0:
                            my_payload[index]['directive'] = key
                            my_payload[index]['args'] = v
                    else:
                        my_payload[index]['block'] = []
                        my_payload[index]['directive'] = key
                        # TODO: Valutare utilizzo di eval
                        my_payload[index]['args'] = ast.literal_eval(*v) if any(isinstance(el, dict) for el in v.values()) else []
                        rebuild(v, my_payload[index]['block'])

                    if cont < max: # Se questo è l'ultimo elemento del sottoblocco, non aggiungo nuovo dict vuoto
                        my_payload.append({})
                        index = len(my_payload) - 1

        else: # caso speciale args con sottoblocco: type(val) == dict
            # ogni entry corrisponde ad un nuovo blocco distinto (vedi location)
            for k, v in val.items():
                if any(isinstance(el, list) for el in v):
                    for entry in v:
                        my_payload.append({})
                        i = len(my_payload)-1

                        my_payload[i]['directive'] = k
                        my_payload[i]['args'] = entry
                elif any(isinstance(el, dict) for el in v):
                    # this could be an 'if' directive, so let's start again with subblock
                    my_payload.append({})
                    i = len(my_payload)-1

                    my_payload[i]['directive'] = k
                    my_payload[i]['args'] = ast.literal_eval(*v[0].keys())
                    my_payload[i]['block'] = []
                    rebuild(v[0], my_payload[i]['block'])
                else:
                    my_payload.append({})
                    i = len(my_payload)-1

                    my_payload[i]['directive'] = k
                    my_payload[i]['args'] = v


for key, val in struct.items():
    # print("---VAL")
    # pprint(val)
    my_payload = []
    # rebuild_wrapper(struct['conf/nginx/./conf.d/default.conf'], my_payload)
    # rebuild_wrapper(struct['conf/nginx/nginx.conf'], my_payload)
    # rebuild_wrapper(struct['conf/nginx/fastcgi_params'], my_payload)
    rebuild_wrapper(val, my_payload)

    print("---MY")
    pprint(my_payload)

    print("---CONFIG")
    # # pprint(payload)
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
