import socket
import random 
import json
import pprint

pp = pprint.PrettyPrinter(indent=2)

def get_from_electrum(method, params=[], server='electrumx.adminsehow.com', port=50001):
    params = [params] if type(params) is not list else params
    try: 
        s = socket.socket()
        s.settimeout(40)
        s.connect((server, port))
        s.send(json.dumps({"id": 0, "method": method, "params": params}).encode() + b'\n')

        return json.loads(s.recv(9999)[:-1].decode())

    except socket.error as e:
        print("Socket.error exception: %s" % e)
        return -1
    except socket.timeout as e:
        print("Socket timed out")
        return -1
    except Exception as e:
        print("Unknown Exception Found: %s" % e)
        return -1


def read_server_list(): 
    with open("servers.json", 'r') as f:
        return json.loads(f.read())

def grab_random_server(serverList):
    serverAddress = None
    while (serverAddress == None):
        serverAddress = random.choice(list(serverList))
        serverObject = serverList[serverAddress]
        if 't' in serverObject:
            serverPort = serverObject['t']
        elif 's' in serverObject:
            serverPort = serverObject['s']
        else: 
            serverAddress = None
    return {
            'serverAddress': str(serverAddress),
            'serverPort'   : int(serverPort)
            }

def check_payment_on_address(addr, serverAddress, serverPort):
    success = False
    addrHistory = get_from_electrum('blockchain.address.get_balance', [addr], server=serverAddress, port=serverPort)
    pp.pprint(addrHistory)

    if addrHistory != -1:
        sats = int(addrHistory['result']['unconfirmed'])

        if sats > 0:
            success = True
            return sats
        else:
            satsConfirmed = int(addrHistory['result']['confirmed'])
            if satsConfirmed > 0:
                success = True
                return satsConfirmed

    return -1

def check_address_history(addr, serverAddress, serverPort):
    success = False
    for x in range(100):
        addrHistory = get_from_electrum('blockchain.address.get_history', 
                [addr], 
                server=serverAddress,
                port=serverPort)

        if addrHistory != -1 and addrHistory['result']:
            addrHistory['result'].append(get_from_electrum( \
                    'blockchain.address.get_balance', 
                    [addr], 
                    server=serverAddress,
                    port=serverPort)['result']['unconfirmed'])

        if addrHistory != -1:
            success == True
            return addrHistory['result']

    return -1

if __name__ == "__main__":
    payment_check = \
        check_address_history('177nUEWD1RCNVcSxNNSRxUWtvMQ4kLJBCK', 'bch.imaginary.cash', 50002)
    if not payment_check:
        print("Address found to be empty, using address!")
    else:
        print("Address confirmed to have utxo: ")
        pp.pprint(payment_check)

    payment_check = \
        check_payment_on_address('17Tb6kwyidMjGkutGfUStKTes8SqL9Rv6x', 'bch.imaginary.cash', 50002)

    if not payment_check:
        print("Address found to be empty, using address!")
    else:
        print("Address confirmed to have utxo: ")
        pp.pprint(payment_check)
