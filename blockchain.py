'''
    Blockchain Project

    Trying to gain a basic understanding of how blockchain apps work. Basic
    BC app that mines for coins and displays the chain. As of 2/23/2021 does
    not allow for transactions.
'''

import hashlib
import json
from time import time
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


# creating the blockchain class
class Blockchain:
    def __init__(self):
        '''
        Function: __init__
        :return:
            Initiates the chain and the transaction list.
        '''
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # creating the genesis block
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        '''
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://0.0.0.0:5000'
        '''

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts URL without scheme
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'],
                                    last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        '''
        Function: new_block
        :return:
            This function creates new blocks and then adds to the existing
            chain.
        '''
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # sets current transaction list to empty
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        '''
        Creates a new transaction which goes into the next Block that is mined.
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction.
        '''

        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
            }
        )

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        '''
        Function: hash
        :param block: Block
        :return:
            This function is used to create the hash for a block. Will create
            a SHA-256 block hash and also ensure that the dictionary is
            ordered.
        '''

        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        '''
        Function: proof_of_work
        :param last_block -- <dict> last Block
            Finds a number p' such that hash(pp') contains leading 5 zeroes,
            where p is the previous proff, and p' is the new proof.
        :return: <int>
        '''

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        '''
        Function: valid_proof
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> the hash of the Previous Block
        :return: <bool> True if correct, False if not.
            this method validates the block.
        '''

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'


app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    '''Making the proof of work algorithm... well... work.'''

    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # rewarding miner for their contribution. 0 specifies new coin has been
    # mined.
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )

    # creating block and adding it to the chain

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'The new block has been forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int,
                        help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.debug = True
    app.run(host='0.0.0.0', port=5000)