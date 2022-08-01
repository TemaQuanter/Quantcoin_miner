from mining_machine import *
from quantcoin_node import QuantcoinNode
import socket
from random import randint
import file_worker
import threading
from glob import glob
import blockchain_validator
import time
import ntplib


ntp_difference = 0


def update_ntp():
    global ntp_difference
    try:
        ntp_difference = int(ntplib.NTPClient().request('pool.ntp.org').tx_time) - time.time()
    except ntplib.NTPException:
        return False
    except socket.gaierror:
        return False
    return True


require_connection = True

exit_program = False

start_time = time.time()
while not update_ntp():
    print(f'\rTrying to get UTC time from the servers for {int(time.time() - start_time)}s', end='')
    print('\r', end='')
    time.sleep(1)


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", randint(30000, 61000)))

host = s.getsockname()[0]
port = 51132

s.close()

print('Starting a new node at the following address')
print(f'host: {host}\nport: {port}')

file_worker_thread = threading.Thread(target=file_worker.task_processor, daemon=True)
file_worker_thread.start()

node = QuantcoinNode(host, port, require_connection)
node.ntp_difference = ntp_difference


def active_nodes_checker():
    global node
    while True:
        node.check_active_nodes()
        time.sleep(60)
        node.update_active_nodes()
        time.sleep(60)


active_nodes_checker_thread = threading.Thread(target=active_nodes_checker, daemon=True)
active_nodes_checker_thread.start()


def establish_connection():
    global require_connection
    global node

    if not require_connection:
        return

    if node.connected_node == None:
        node.connect_with_new_node(True)
        while node.connected_node == None:
            time.sleep(0.2)


def establish_new_connection():
    global require_connection
    global node

    connected_node = node.connected_node

    node.disconnect_with_node(connected_node)
    try:
        node.nodes_list.remove([connected_node.host, int(connected_node.port)])
    except ValueError:
        pass
    node.connected_node = None

    file_worker.put_json('nodes_list.json', {'nodes': node.nodes_list})

    if not require_connection:
        return

    if node.connected_node == None:
        node.connect_with_new_node(True)
        while node.connected_node == None:
            time.sleep(0.2)


def download_blocks(starting_block):
    current_block = starting_block
    node.have_all_blocks = False
    while not node.have_all_blocks:
        print(f'\rDownloading block: {current_block}', end='')
        node.got_block = False
        node.send_to_node(node.connected_node, {'header': 'request_block', 'data': current_block})
        while not node.got_block:
            if node.connected_node == None:
                establish_connection()
                node.send_to_node(node.connected_node, {'header': 'request_block', 'data': current_block})
            time.sleep(0.01)
        if current_block % 5:
            result = blockchain_validator.blockchain_validator()
            if result != 'OK':
                node.have_all_blocks = True
                while not (blockchain_validator.blockchain_validator() == 'OK'):
                    file_worker.remove_file(f'Blockchain/{current_block}.json')
                    current_block -= 1
                establish_new_connection()
        current_block += 1


def download_pending_block():
    establish_connection()
    node.got_block = False
    node.send_to_node(node.connected_node, {'header': 'request_block', 'data': 'pending_block'})
    while not node.got_block:
        if node.connected_node == None:
            establish_connection()
            node.send_to_node(node.connected_node, {'header': 'request_block', 'data': 'pending_block'})
        time.sleep(0.01)


def download_pending_transactions():
    establish_connection()
    node.got_block = False
    node.send_to_node(node.connected_node, {'header': 'request_block', 'data': 'pending_transactions'})
    while not node.got_block:
        if node.connected_node == None:
            establish_connection()
            node.send_to_node(node.connected_node, {'header': 'request_block', 'data': 'pending_transactions'})
        time.sleep(0.01)


def load_pending():
    if require_connection:
        print('Downloading pending transactions...')
        download_pending_transactions()
        print('Finished downloading pending transactions!')


def check_blockchain():
    file_array = set([el.replace('\\', '/').lstrip('Blockchain/').rstrip('.json') for el in glob('Blockchain/*.json')])
    for file_name in file_array:
        if (not file_name.isnumeric()) and (file_name != 'pending_transactions'):
            try:
                file_worker.remove_file(f'Blockchain/{file_name}.json')
            except Exception as e:
                pass
    for i in range(len(file_array) - 1):
        if str(i) in file_array:
            file_array.discard(str(i))
    file_array.discard('pending_transactions')
    for file_name in file_array:
        try:
            file_worker.remove_file(f'Blockchain/{file_name}.json')
        except Exception as e:
            pass
    current_block = len(glob('Blockchain/*.json')) - 2
    while blockchain_validator.blockchain_validator() != 'OK':
        try:
            file_worker.remove_file(f'Blockchain/{current_block}.json')
        except FileNotFoundError:
            pass
        current_block -= 1


def update():
    next_public_keys_data_final_block = -1

    check_blockchain()
    file_arr = glob('public_keys_data_final_block_*.json')
    for file_name in file_arr:
        next_public_keys_data_final_block = max(next_public_keys_data_final_block, int(file_name.strip('public_keys_data_final_block_.json')))
    for file_name in file_arr:
        if file_name.strip('public_keys_data_final_block_.json') != str(next_public_keys_data_final_block):
            file_worker.remove_file(file_name)
    if require_connection:
        print('Started downloading new blocks...')
        download_blocks(next_public_keys_data_final_block + 1)
        print('\nFinished downloading new blocks!')
    check_blockchain()
    file_arr = glob('public_keys_data_final_block_*.json')
    for file_name in file_arr:
        next_public_keys_data_final_block = max(next_public_keys_data_final_block, int(file_name.strip('public_keys_data_final_block_.json')))
    for file_name in file_arr:
        if file_name.strip('public_keys_data_final_block_.json') != str(next_public_keys_data_final_block):
            file_worker.remove_file(file_name)

    load_pending()

    # try:
    #     with open(f'public_keys_data_final_block_{next_public_keys_data_final_block}.json') as file:
    #         public_keys = json.load(file)
    # except FileNotFoundError:
    #     pass

miner_address = '0x0'

try:
    with open('miner_address.txt') as file:
        miner_address = file.readline().strip()
except Exception as e:
    print(e)
    exit(0)

update()

while True:
    update_ntp()
    all_nfts = set(file_worker.get_json('all_nfts.json'))
    block_number = create_block(ntp_difference, all_nfts)
    node.expected_block = block_number
    print(f'Start mining!\nBlock: {block_number}')
    block = mine_block(block_number, miner_address)
    if block != None:
        block['header'] = 'new_block'
        block['block_index'] = block_number
        node.send_to_nodes(block)
        print('Victory!')
    else:
        print('Defeat')