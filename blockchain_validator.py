import time
import glob
from hash_calculater import get_hash
from cryptographer import get_hash_from_signature
import json
from os.path import exists
import file_worker


def get_block(block_number):
    block = dict()
    try:
        with open(f'Blockchain/{block_number}.json') as file:
            block = json.load(file)
    except FileNotFoundError:
        pass
    return block


def is_valid_transaction(transaction):
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
    else:
        public_key = split_transaction[0]
        if is_nft(split_transaction[2]):
            pass
        elif str(split_transaction[2]).count('e') != 0:
            # print(6)
            return False
    if int(split_transaction[3]) < 1:
        return False
    signature = split_transaction[-1]
    transaction = ';'.join(split_transaction[:-1])
    transaction_hash = get_hash(transaction)
    if hex(get_hash_from_signature(signature, public_key))[2:] == transaction_hash:
        return True
    # print(7)
    return False


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


def is_nft(string):
    all_the_possible_symbols = '0123456789abcdef'
    for el in string:
        if not (el in all_the_possible_symbols):
            return False
    return len(string) == 64


def fail_check(error_message):
    return 'INVALID CHAIN!', error_message


def blockchain_validator():
    all_nfts = set()

    public_keys = dict()

    number_of_blocks = len(glob.glob('Blockchain/[0-9]*.json'))

    public_keys_data = glob.glob('public_keys_data_final_block_*.json')
    for i in range(len(public_keys_data)):
        public_keys_data[i] = int(public_keys_data[i].strip('public_keys_data_final_block_.json'))

    st = set()

    start_block = -1

    if len(public_keys_data) > 3:
        public_keys_data.sort()
        for el in public_keys_data[:-3]:
            try:
                file_worker.remove_file(f'public_keys_data_final_block_{el}.json')
            except FileNotFoundError:
                pass
            except PermissionError:
                pass

    if len(public_keys_data) > 0:
        start_block = max(public_keys_data)
        with open(f'public_keys_data_final_block_{start_block}.json') as file:
            public_keys = json.load(file)
        for key in public_keys.keys():
            if key != 'st':
                public_keys[key]['nfts'] = set(public_keys[key]['nfts'])
        st = set(public_keys['st'])

    for block_index in range(start_block + 1, number_of_blocks):
        if not exists(f'Blockchain/{block_index}.json'):
            return fail_check('The order of blocks is incorrect')
        current_block_difficulty = 0
        if block_index != 0:
            previous_block_number = max(0, block_index - 10)
            time_of_previous_block = get_block(previous_block_number)['time']
            current_difficulty = 0
            for block_number in range(previous_block_number, block_index):
                current_difficulty += int(get_block(block_number)['difficulty'])
            current_difficulty //= block_index - previous_block_number
            time_of_current_block = get_block(block_index)['time']
            real_mining_time_per_block = max(
                (time_of_current_block - time_of_previous_block) // (block_index - previous_block_number), 1)
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
        else:
            current_block_difficulty = 20
        file_name = f'Blockchain/{block_index}.json'
        if block_index == number_of_blocks - 1:
            time.sleep(0.1)
        miner_fee = 0
        block_data = []
        try:
            with open(file_name) as file:
                block_data = json.load(file)
        except FileNotFoundError:
            return fail_check('The order of blocks is incorrect')
        for i in range(len(block_data['transactions'])):
            transaction_hash_number = int(get_hash(block_data['transactions'][i]), 16)
            if transaction_hash_number in st:
                return fail_check(f'The same transaction already exists\n{block_data["transactions"][i]}')
            st.add(transaction_hash_number)
            transaction = block_data['transactions'][i].split(';')
            if not is_valid_transaction(block_data['transactions'][i]):
                return fail_check(f'The transaction is invalid\n{block_data["transactions"][i]}')
            if (not transaction[0] in public_keys.keys()) and (transaction[0] != '0x0000000000000000'):
                public_keys[transaction[0]] = dict()
                public_keys[transaction[0]]['balance'] = 0
                public_keys[transaction[0]]['nfts'] = set()
                public_keys[transaction[0]]['transaction_number'] = 1
            if transaction[0] != '0x0000000000000000':
                if is_nft(transaction[2]):
                    if not (int(transaction[2], 16) in public_keys[transaction[0]]['nfts']):
                        return fail_check(f'The address does not possess the NFT\n{transaction[0]}\n{transaction[2]}')
                    public_keys[transaction[0]]['nfts'].discard(int(transaction[2], 16))
                    public_keys[transaction[0]]['balance'] -= int(transaction[3])
                    if public_keys[transaction[0]]['balance'] < 0:
                        return fail_check(f'The address\'s balance becomes less than zero\n{transaction[0]}')
                else:
                    public_keys[transaction[0]]['balance'] -= int(transaction[2])
                    if public_keys[transaction[0]]['balance'] < 0:
                        return fail_check(f'The address\'s balance becomes less than zero\n{transaction[0]}')
                public_keys[transaction[0]]['transaction_number'] = max(
                    public_keys[transaction[0]]['transaction_number'], int(transaction[-2]) + 1)
            if (not transaction[1] in public_keys.keys()) and (transaction[1] != '0x0000000000000000'):
                public_keys[transaction[1]] = dict()
                public_keys[transaction[1]]['balance'] = 0
                public_keys[transaction[1]]['nfts'] = set()
                public_keys[transaction[1]]['transaction_number'] = 1
            if transaction[1] != '0x0000000000000000':
                if is_nft(transaction[2]):
                    if transaction[0] == '0x0000000000000000' and (int(transaction[2], 16) in all_nfts):
                        return fail_check(f'The NFT is created twice\n{transaction[0]}\n{transaction[2]}')
                    public_keys[transaction[1]]['nfts'].add(int(transaction[2], 16))
                    if transaction[0] == '0x0000000000000000':
                        public_keys[transaction[1]]['balance'] -= int(transaction[3])
                    if public_keys[transaction[1]]['balance'] < 0:
                        return fail_check(
                            f'The creator of the NFT is not solvent for paying miner\'s fee\n{transaction[1]}\n{transaction[2]}')
                else:
                    public_keys[transaction[1]]['balance'] += int(transaction[2]) - int(transaction[3])
                    if public_keys[transaction[1]]['balance'] < 0:
                        return fail_check(f'The balance of the address becomes less than zero\n{transaction[1]}')
            if is_nft(transaction[2]):
                all_nfts.add(int(transaction[2], 16))
            miner_fee += int(transaction[3])
        if (not block_data['miner'] in public_keys.keys()) and (block_data['miner'] != '0x0000000000000000'):
            public_keys[block_data['miner']] = dict()
            public_keys[block_data['miner']]['balance'] = 0
            public_keys[block_data['miner']]['nfts'] = set()
            public_keys[block_data['miner']]['transaction_number'] = 1
        if block_data['miner'] != '0x0000000000000000':
            public_keys[block_data['miner']]['balance'] += 50 + miner_fee
        if (file_name == 'Blockchain/0.json') and (block_data['signature_of_previous_block'] != '0x0'):
            return fail_check('The signature_of_previous_block of the initial block is invalid')
        elif (file_name != 'Blockchain/0.json') and (
                block_data['signature_of_previous_block'] != get_block(int(file_name.strip('Blockchain.json/')) - 1)[
            'signature']):
            return fail_check(
                f'The signature of the block {block_index} does not match the signature of the block {block_index - 1}')
        if not is_valid_block(get_block(int(file_name.strip('Blockchain.json/')))):
            return fail_check(f'The block {block_index} is invalid')
        if current_block_difficulty != int(block_data['difficulty']):
            return fail_check(
                f'Incorrect mining difficulty in block {block_index}\n{current_block_difficulty}\n{int(block_data["difficulty"])}')

    for key in public_keys.keys():
        if key != 'st':
            public_keys[key]['nfts'] = list(public_keys[key]['nfts'])
    public_keys['st'] = list(st)
    with open(f'public_keys_data_final_block_{number_of_blocks - 1}.json', 'w') as file:
        json.dump(public_keys, file)
    with open('all_nfts.json', 'w') as file:
        json.dump({'all_nfts': list(all_nfts)}, file)

    return 'OK'


if __name__ == "__main__":
    print(blockchain_validator())