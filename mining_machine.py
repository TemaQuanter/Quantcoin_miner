from hash_calculater import get_hash
from cryptographer import get_hash_from_signature
import glob
import json
from blockchain_validator import blockchain_validator
import file_worker
import time


def is_nft(string):
    all_the_possible_symbols = '0123456789abcdef'
    for el in string:
        if not (el in all_the_possible_symbols):
            return False
    return len(string) == 64


def is_valid_transaction(transaction, public_keys, all_nfts):
    split_transaction = transaction.split(';')
    if len(split_transaction) != 6:
        # print(1)
        return False
    transaction_number = None
    try:
        int(split_transaction[3])
        transaction_number = int(split_transaction[4])
        if is_nft(split_transaction[2]):
            int(split_transaction[2], 16)
        else:
            int(split_transaction[2])
    except:
        # print(2)
        return False
    for el in split_transaction:
        if str(el).count('.') + str(el).count(',') != 0:
            # print(3)
            return False
    if str(split_transaction[3]).count('e') != 0:
        # print(4)
        return False
    if str(split_transaction[4]).count('e') != 0:
        # print(5)
        return False
    public_key = None
    if is_nft(split_transaction[2]) and split_transaction[0] == '0x0000000000000000':
        public_key = split_transaction[1]
        try:
            if public_keys[public_key]['balance'] - int(split_transaction[3]) < 0:
                # print(6)
                return False
            if int(split_transaction[2], 16) in all_nfts:
                return False
        except Exception as e:
            return False
    else:
        public_key = split_transaction[0]
        try:
            if transaction_number < public_keys[public_key]['transaction_number']:
                # print(7)
                return False
        except Exception as e:
            return False
        if is_nft(split_transaction[2]):
            try:
                if public_keys[public_key]['balance'] - int(split_transaction[3]) < 0:
                    # print(8)
                    return False
                if not (int(split_transaction[2], 16) in public_keys[public_key]['nfts']):
                    return False
            except Exception as e:
                return False
        elif str(split_transaction[2]).count('e') != 0:
            # print(9)
            return False
        else:
            if public_keys[public_key]['balance'] - int(split_transaction[2]) < 0:
                return False
            if int(split_transaction[2]) - int(split_transaction[3]) <= 0:
                return False
    if int(split_transaction[3]) < 1:
        return False
    signature = split_transaction[-1]
    transaction = ';'.join(split_transaction[:-1])
    transaction_hash = get_hash(transaction)
    if hex(get_hash_from_signature(signature, public_key))[2:] == transaction_hash:
        return True
    # print(10)
    return False


def get_block(block_number):
    block = dict()
    with open(f'Blockchain/{block_number}.json') as file:
        block = json.load(file)
    return block


def remove_mined_transactions(all_nfts):
    target_number = -2
    all_files = glob.glob('public_keys_data_final_block_*.json')
    for file in all_files:
        target_number = max(target_number, int(file.strip('public_keys_data_final_block_.json')))
    if target_number == -2:
        return
    data = file_worker.get_json(f'public_keys_data_final_block_{target_number}.json')
    data_set = set(data['st'])
    all_transactions = file_worker.get_json('Blockchain/pending_transactions.json')['transactions']
    potential_transactions = []
    for transaction in all_transactions:
        if (not (int(get_hash(transaction), 16) in data_set)) and is_valid_transaction(transaction, data, all_nfts):
            potential_transactions.append(transaction)
    file_worker.put_json('Blockchain/pending_transactions.json', {'transactions': potential_transactions})


def create_zero_block(ntp_difference):
    with open('Blockchain/pending_block_not_ready.json', 'w') as file:
        json.dump({'transactions': [], 'time': time.time() + ntp_difference, 'difficulty': 20, 'miner': None, 'signature_of_previous_block': '0x0', 'signature': None}, file)
    try:
        file_worker.rename_file('Blockchain/pending_block_not_ready.json', 'Blockchain/pending_block.json')
    except FileExistsError:
        file_worker.remove_file('Blockchain/pending_block_not_ready.json')
    except PermissionError:
        file_worker.remove_file('Blockchain/pending_block_not_ready.json')
    return 0


def create_block(ntp_difference, all_nfts):
    if 'Blockchain/pending_block_not_ready.json' in glob.glob('Blockchain/pending_block_not_ready.json'):
        while not ('Blockchain/pending_block.json' in glob.glob('Blockchain/pending_block.json')):
            pass
        return len(glob.glob('Blockchain/[0-9]*.json'))
    if 'Blockchain/pending_block.json' in glob.glob('Blockchain/pending_block.json'):
        return len(glob.glob('Blockchain/[0-9]*.json'))
    file = open('Blockchain/pending_block_not_ready.json', 'w')
    file.close()
    existing_blocks = glob.glob('Blockchain/[0-9]*.json')
    new_block_number = len(existing_blocks)
    if new_block_number == 0:
        create_zero_block(ntp_difference)
        return new_block_number
    public_keys = dict()
    if not f'public_keys_data_final_block_{len(existing_blocks) - 1}.json' in glob.glob('public_keys_data_final_block_*.json'):
        is_valid_blockchain = blockchain_validator()
        if is_valid_blockchain != 'OK':
            print(is_valid_blockchain[0])
            print(is_valid_blockchain[1])
            exit(0)
    remove_mined_transactions(all_nfts)
    with open(f'public_keys_data_final_block_{len(existing_blocks) - 1}.json') as file:
        public_keys = json.load(file)
    for key in public_keys.keys():
        if key != 'st':
            public_keys[key]['nfts'] = set(public_keys[key]['nfts'])
    transactions = get_transactions(public_keys, all_nfts)
    previous_block_number = max(0, new_block_number - 10)
    time_of_previous_block = get_block(previous_block_number)['time']
    current_difficulty = 0
    for block_number in range(previous_block_number, new_block_number):
        current_difficulty += int(get_block(block_number)['difficulty'])
    current_difficulty //= new_block_number - previous_block_number
    time_of_current_block = time.time() + ntp_difference
    real_mining_time_per_block = max((time_of_current_block - time_of_previous_block) // (new_block_number - previous_block_number), 1)
    current_block_difficulty = current_difficulty
    if real_mining_time_per_block > 239:
        current_block_difficulty = current_difficulty - 1
    elif real_mining_time_per_block < 61:
        current_block_difficulty = current_difficulty + 1
    elif real_mining_time_per_block > 479:
        current_block_difficulty = current_difficulty - 2
    elif real_mining_time_per_block < 31:
        current_block_difficulty = current_difficulty + 2
    current_block_difficulty = min(256, max(1, current_block_difficulty))
    with open('Blockchain/pending_block_not_ready.json', 'w') as file:
        json.dump({'transactions': [transaction[1] for transaction in transactions], 'time': time_of_current_block, 'difficulty': current_block_difficulty, 'miner': None, 'signature_of_previous_block': get_block(new_block_number - 1)['signature'], 'signature': None}, file)
    try:
        file_worker.rename_file('Blockchain/pending_block_not_ready.json', 'Blockchain/pending_block.json')
    except FileExistsError:
        file_worker.remove_file('Blockchain/pending_block_not_ready.json')
    except PermissionError:
        file_worker.remove_file('Blockchain/pending_block_not_ready.json')
    return new_block_number


def mine_block(block_number, public_key):
    block = get_block('pending_block')
    difficulty = block['difficulty']
    block['miner'] = public_key
    block.pop('signature')
    block_hash = get_hash(str(block))
    signature = 0
    counter = 1
    while True:
        counter = (counter + 1) % 300
        if counter == 0:
            blockchain_validator_verdict = blockchain_validator()
            if f'Blockchain/{block_number}.json' in glob.glob(f'Blockchain/{block_number}.json') and blockchain_validator_verdict == 'OK':
                try:
                    file_worker.remove_file('Blockchain/pending_block.json')
                    file_worker.remove_file('Blockchain/pending_block_not_ready.json')
                except FileNotFoundError:
                    return None
                return None
            if blockchain_validator_verdict != 'OK':
                file_worker.remove_file(f'Blockchain/{block_number}.json')
        candidate = bin(int(get_hash(block_hash + hex(signature)), 16))[-difficulty:]
        key_letter = candidate[0]
        flag = True
        for el in candidate:
            if el != key_letter:
                flag = False
                break
        if flag:
            block['signature'] = hex(signature)
            blockchain_validator_verdict = blockchain_validator()
            if f'Blockchain/{block_number}.json' in glob.glob(f'Blockchain/{block_number}.json') and blockchain_validator_verdict == 'OK':
                try:
                    file_worker.remove_file('Blockchain/pending_block.json')
                    file_worker.remove_file('Blockchain/pending_block_not_ready.json')
                except FileNotFoundError:
                    return None
                return None
            if blockchain_validator_verdict != 'OK':
                file_worker.remove_file(f'Blockchain/{block_number}.json')
            # with open(f'Blockchain/{block_number}.json', 'w') as file:
            #     json.dump(block, file)
            result = file_worker.post_new_block(f'Blockchain/{block_number}.json', block)
            file_worker.remove_file('Blockchain/pending_block.json')
            if result == 'Fail':
                try:
                    file_worker.remove_file('Blockchain/pending_block.json')
                    file_worker.remove_file('Blockchain/pending_block_not_ready.json')
                except FileNotFoundError:
                    return None
                return None
            return block
        signature += 1


def is_valid_block(block):
    signature = block['signature']
    difficulty = block['difficulty']
    block.pop('signature')
    block = str(block)
    signed_block_hash = bin(int(get_hash(get_hash(block) + signature), 16))[-difficulty:]
    key_letter = signed_block_hash[0]
    flag = True
    for el in signed_block_hash:
        if el != key_letter:
            flag = False
            break
    return flag


def apply_transaction(transaction, public_keys, all_nfts):
    split_transaction = transaction.split(';')
    if len(split_transaction) != 6:
        # print(1)
        return (public_keys, False)
    transaction_number = None
    try:
        int(split_transaction[3])
        transaction_number = int(split_transaction[4])
        if is_nft(split_transaction[2]):
            int(split_transaction[2], 16)
        else:
            int(split_transaction[2])
    except:
        # print(2)
        return (public_keys, False)
    for el in split_transaction:
        if str(el).count('.') + str(el).count(',') != 0:
            # print(3)
            return (public_keys, False)
    if str(split_transaction[3]).count('e') != 0:
        # print(4)
        return (public_keys, False)
    if str(split_transaction[4]).count('e') != 0:
        # print(5)
        return (public_keys, False)
    public_key = None
    if is_nft(split_transaction[2]) and split_transaction[0] == '0x0000000000000000':
        public_key = split_transaction[1]
        try:
            if public_keys[public_key]['balance'] - int(split_transaction[3]) < 0:
                # print(6)
                return (public_keys, False)
            if int(split_transaction[2], 16) in all_nfts:
                return (public_keys, False)
        except Exception as e:
            return (public_keys, False)
        public_keys[public_key]['balance'] -= int(split_transaction[3])
    else:
        public_key = split_transaction[0]
        try:
            if transaction_number < public_keys[public_key]['transaction_number']:
                # print(7)
                return (public_keys, False)
        except Exception as e:
            return (public_keys, False)
        if is_nft(split_transaction[2]):
            try:
                if public_keys[public_key]['balance'] - int(split_transaction[3]) < 0:
                    # print(8)
                    return (public_keys, False)
                if not (int(split_transaction[2], 16) in public_keys[public_key]['nfts']):
                    return (public_keys, False)
            except Exception as e:
                return (public_keys, False)
            public_keys[public_key]['balance'] -= int(split_transaction[3])
            public_keys[public_key]['nfts'].remove(int(split_transaction[2], 16))
        elif str(split_transaction[2]).count('e') != 0:
            # print(9)
            return (public_keys, False)
        else:
            if public_keys[public_key]['balance'] - int(split_transaction[2]) < 0:
                return (public_keys, False)
            if int(split_transaction[2]) - int(split_transaction[3]) <= 0:
                return (public_keys, False)
            public_keys[public_key]['balance'] -= int(split_transaction[2])
    return (public_keys, True)


def get_transactions(public_keys, all_nfts):
    transactions = []
    data = dict()
    with open('Blockchain/pending_transactions.json') as file:
        data = json.load(file)
    for transaction in data['transactions']:
        transaction = transaction.strip()
        if is_valid_transaction(transaction, public_keys, all_nfts):
            transactions.append([int(transaction.split(';')[-3]), transaction])
    transactions.sort(reverse = True)
    final_transactions = []
    for transaction in transactions:
        public_keys, result = apply_transaction(transaction[1], public_keys, all_nfts)
        if result:
            final_transactions.append(transaction)
    return final_transactions[:min(1000, len(final_transactions))]