from p2pnetwork.node import Node
from p2pnetwork.nodeconnection import NodeConnection
import glob
import blockchain_validator
import file_worker
import time
from os.path import exists


class ExcludeNode(Node):
    def __init__(self, dictionary):
        super(ExcludeNode, self).__init__(dictionary['host'], dictionary['port'], dictionary['id'], None, 5)
        for key, value in dictionary.items():
            setattr(self, key, value)


class QuantcoinNode(Node):

    nodes_list = []

    connected_node = None

    have_all_blocks = False

    got_block = False

    expected_block = None

    previous_block_time = 0

    ntp_difference = 0

    active_nodes = set()

    # Python class constructor
    def __init__(self, host, port, require_connection=True, id=None, callback=None, max_connections=10):
        if require_connection:
            super(QuantcoinNode, self).__init__(host, port, id, callback, max_connections)

            self.start()

        # Loading the list of remembered nodes of the network

        if (len(glob.glob('nodes_list.json')) == 0) or (not require_connection):
            file_worker.put_json('nodes_list.json', {'nodes': []})
            # with open('nodes_list.json', 'w') as file:
            #     json.dump({'nodes': [[host, int(port)]]}, file)
        nodes_list_unserialized = file_worker.get_json('nodes_list.json')
        # with open('nodes_list.json', 'r') as file:
        #     nodes_list_unserialized = json.loads(file.read())
        for node in nodes_list_unserialized['nodes']:
            self.nodes_list.append(node)

        # Trying to establish the connection with any available node in the network

        if require_connection:
            self.connect_with_new_node(True)

        if (not require_connection):
            super(QuantcoinNode, self).__init__(host, port, id, callback, max_connections)

            self.start()

    def connect_with_new_node(self, require_connection):
        start_time = time.time()
        nodes_list_copy = [nd for nd in self.nodes_list]
        for node in nodes_list_copy:
            cur_time = time.time()
            if cur_time - start_time > 120:
                file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
                break
            print(f'Trying to connect to {node[0]}:{node[1]}')
            if self.connect_with_node(node[0], node[1]):
                print('Successfully connected to a node!')

                # Getting the latest list of available nodes in the network

                self.send_to_node(self.connected_node, {'header': 'nodes_list_request'})
                file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
                return True
            else:
                try:
                    self.nodes_list.remove(node)
                except ValueError:
                    pass
        file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
        if not require_connection:
            return False
        while True:
            print()
            print('Failed to connect to a remote node')
            print('Manual connection is required')
            print('Enter host and port of the node you want to connect to')
            host = input('host: ')
            port = int(input('port: '))
            if self.connect_with_node(host, port):
                break
        print('Successfully connected to a node!')

        # Getting the latest list of available nodes in the network

        self.send_to_node(self.connected_node, {'header': 'nodes_list_request'})
        return True

    def outbound_node_connected(self, connected_node):
        self.send_to_node(connected_node, {'header': 'active?'})
        if self.connected_node == None:
            self.connected_node = connected_node
        if not ([connected_node.host, int(connected_node.port)] in self.nodes_list):
            self.nodes_list.append([connected_node.host, int(connected_node.port)])
            file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
            self.send_to_nodes({'header': 'new_node', 'new_node': [connected_node.host, int(connected_node.port)]})
        pass
        # print("outbound_node_connected: " + connected_node.id)

    def inbound_node_connected(self, connected_node):
        self.send_to_node(connected_node, {'header': 'active?'})
        if not ([connected_node.host, int(connected_node.port)] in self.nodes_list):
            self.nodes_list.append([connected_node.host, int(connected_node.port)])
            file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
            # with open('nodes_list.json', 'w') as file:
            #     json.dump({'nodes': self.nodes_list}, file)
            self.send_to_nodes({'header': 'new_node', 'new_node': [connected_node.host, int(connected_node.port)]})
        pass
        # print("inbound_node_connected: " + connected_node.id)

    def check_active_nodes(self):
        self.active_nodes.clear()
        for n in self.nodes_inbound:
            self.send_to_node(n, {'header': 'active?'})
        for n in self.nodes_outbound:
            self.send_to_node(n, {'header': 'active?'})

    def update_active_nodes(self):
        nodes_inbound_copy = [nd for nd in self.nodes_inbound]
        for n in nodes_inbound_copy:
            if not (n in self.active_nodes):
                if n == self.connected_node:
                    self.connected_node = None
                n.stop()
                try:
                    self.nodes_inbound.remove(n)
                except ValueError:
                    pass
                try:
                    self.nodes_list.remove([n.host, int(n.port)])
                except ValueError:
                    pass
        nodes_outbound_copy = [nd for nd in self.nodes_outbound]
        for n in nodes_outbound_copy:
            if not (n in self.active_nodes):
                if n == self.connected_node:
                    self.connected_node = None
                n.stop()
                try:
                    self.nodes_outbound.remove(n)
                except ValueError:
                    pass
                try:
                    self.nodes_list.remove([n.host, int(n.port)])
                except ValueError:
                    pass
        file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})

    def inbound_node_disconnected(self, connected_node):
        try:
            connected_node.stop()
            self.nodes_inbound.remove(connected_node)
        except ValueError:
            pass
        try:
            connected_node.stop()
            self.nodes_outbound.remove(connected_node)
        except ValueError:
            pass

    def outbound_node_disconnected(self, connected_node):
        try:
            connected_node.stop()
            self.nodes_inbound.remove(connected_node)
        except ValueError:
            pass
        try:
            connected_node.stop()
            self.nodes_outbound.remove(connected_node)
        except ValueError:
            pass

    def node_message(self, connected_node, data):
        try:
            if not ('header' in data.keys()):
                return
            elif data['header'] == 'active?':
                self.send_to_node(connected_node, {'header': 'active!'})
            elif data['header'] == 'active!':
                self.active_nodes.add(connected_node)
            elif data['header'] == 'nodes_list_request':
                reply = file_worker.get_json('nodes_list.json')
                # with open('nodes_list.json', 'r') as file:
                #     reply = json.loads(file.read())
                self.send_to_node(connected_node, {'header': 'nodes_list', 'data': reply})
            elif data['header'] == 'nodes_list':
                self.nodes_list.clear()
                for node in data['data']['nodes']:
                    self.nodes_list.append(node)
                file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
                # with open('nodes_list.json', 'w') as file:
                #     json.dump({'nodes': self.nodes_list}, file)
            elif data['header'] == 'disconnecting':
                self.nodes_list.remove([connected_node.host, int(connected_node.port)])
                self.disconnect_with_node(connected_node)
                try:
                    connected_node.stop()
                    self.nodes_inbound.remove(connected_node)
                except ValueError:
                    pass
                try:
                    connected_node.stop()
                    self.nodes_outbound.remove(connected_node)
                except ValueError:
                    pass
                file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
                # with open('nodes_list.json', 'w') as file:
                #     json.dump({'nodes': self.nodes_list}, file)
                if self.connected_node == connected_node:
                    self.connected_node = None
                    # request node to reconnect to any other node
                    time.sleep(0.001)
                    # self.connect_with_new_node(True)
            elif data['header'] == 'request_block':
                block_index = data['data']
                try:
                    reply = file_worker.get_json(f'Blockchain/{block_index}.json')
                    # with open(f'Blockchain/{block_index}.json', 'r') as file:
                    #     reply = json.loads(file.read())
                    reply['header'] = 'block'
                    reply['block_index'] = block_index
                    self.send_to_node(connected_node, reply)
                except FileNotFoundError:
                    self.send_to_node(connected_node, {'header': 'BlockNotFound'})
            elif data['header'] == 'BlockNotFound':
                self.have_all_blocks = True
                self.got_block = True
            elif data['header'] == 'block':
                if self.got_block == True:
                    return
                data.pop('header')
                block_index = data.pop('block_index')
                if block_index == 'pending_transactions':
                    file_worker.put_json('Blockchain/pending_transactions.json', data)
                else:
                    file_worker.post_new_block(f'Blockchain/{block_index}.json', data)
                # try:
                #     with open(f'Blockchain/{block_index}.json', 'w') as file:
                #         json.dump(data, file)
                # except Exception as e:
                #     print(e)
                self.got_block = True
            elif data['header'] == 'pending_transaction':
                pending_transactions_file = file_worker.get_json('Blockchain/pending_transactions.json')
                if pending_transactions_file['transactions'].count(data['transaction']) == 0:
                    self.send_to_nodes(data, [connected_node])
                    if blockchain_validator.is_valid_transaction(data['transaction']):
                        pending_transactions_file['transactions'].append(data['transaction'])
                        file_worker.put_json(f'Blockchain/pending_transactions.json', pending_transactions_file)
                # with open(f'Blockchain/pending_transactions.json', 'w') as file:
                #     json.dump(data, file)
            elif data['header'] == 'new_block':
                if exists(f'Blockchain/{data["block_index"]}.json') or (data['block_index'] != self.expected_block):
                    return
                if data['time'] > (time.time() + self.ntp_difference):
                    return
                if data['time'] < self.previous_block_time:
                    return
                self.previous_block_time = data['time']
                self.send_to_nodes(data, [connected_node])
                data.pop('header')
                block_index = data.pop('block_index')
                file_worker.post_new_block(f'Blockchain/{block_index}.json', data)
                # with open(f'Blockchain/pending_transactions.json', 'w') as file:
                #     json.dump(data, file)
            elif data['header'] == 'new_node':
                if not (data['new_node'] in self.nodes_list):
                    self.send_to_nodes(data)
                    self.nodes_list.append(data['new_node'])
                    file_worker.put_json('nodes_list.json', {'nodes': self.nodes_list})
        except Exception as e:
            pass
        except BaseException as e:
            pass

    def node_disconnected(self, node):
        # print('Node is disconnected: ' + str(node.port))
        pass

    def node_disconnect_with_outbound_node(self, connected_node):
        try:
            self.nodes_inbound.remove(connected_node)
        except ValueError:
            pass
        try:
            self.nodes_outbound.remove(connected_node)
        except ValueError:
            pass
        # print("node wants to disconnect with other outbound node: " + str(connected_node.port))
        pass

    def stop(self):
        print('Notifying all the connected nodes of disconnection...')
        if len(self.all_nodes) > 0:
            self.send_to_nodes({'header': 'disconnecting'})
        print('Stopping local node...\nThis might take some time')
        super().stop()

    # OPTIONAL
    # If you need to override the NodeConection as well, you need to
    # override this method! In this method, you can initiate
    # you own NodeConnection class.
    def create_new_connection(self, connection, id, host, port):
        return QuantcoinNodeConnection(self, connection, id, host, port)


class QuantcoinNodeConnection(NodeConnection):
    # Python class constructor
     def __init__(self, main_node, sock, id, host, port):
        super(QuantcoinNodeConnection, self).__init__(main_node, sock, id, host, port)

    # Check yourself what you would like to change and override! See the
    # documentation and code of the nodeconnection class.