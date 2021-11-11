import json
import requests
import base58
from datetime import datetime

endpoint = 'https://api.bitclout.com'

def getChainHeight():
    response = requests.post(endpoint+'/api/v0/get-app-state', json={ "PublicKeyBase58Check":"BC1YLint2QNJWyNMX8kAiiTiYjT8yrTNYtzXKbGhXRoj7dPyNHboQLY"})
    respdata = json.loads(response.text)
    chainheight = respdata['BlockHeight']
    return chainheight

def getBlockInfo(height):
    # Call /api/v1/block to get details about a block passed to the function
    data = { 'Height':height, 'FullBlock':True }
    response = requests.post(endpoint+"/api/v1/block", json=data)

    # Return the JSON response
    respdata = json.loads(response.text)
    return respdata

def processBlockJSON(json):
    transactions = json['Transactions']
    transactionCount = len(transactions)
    header = json['Header']
    height = header['Height']
    timestamp = header['TstampSecs']
    dt_object = datetime.fromtimestamp(timestamp)
    date_time = dt_object.strftime("%m/%d/%Y, %H:%M:%S")
    
    for transaction in transactions:
        transactionType = transaction['TransactionType']

        event = ''

        if(transactionType == 'BLOCK_REWARD'):
            outputs = transaction['TransactionMetadata']['AffectedPublicKeys'][0]
            k = outputs['PublicKeyBase58Check']
            a = transaction['TransactionMetadata']['TxnOutputs'][0]['AmountNanos']
            event = {'type':'BLOCK_REWARD', 'PublicKey':k, 'amount':a}

        elif(transactionType == 'FOLLOW'):
            affectedkeys = transaction['TransactionMetadata']['AffectedPublicKeys']
            follower = followed = ''
            for a in affectedkeys:
                if(a['Metadata'] == 'FollowedPublicKeyBase58Check'):
                    followed = a['PublicKeyBase58Check']
                elif(a['Metadata'] == 'BasicTransferOutput'):
                    follower = a['PublicKeyBase58Check']
            fstr = 'FOLLOW'
            if(transaction['TransactionMetadata']['FollowTxindexMetadata']['IsUnfollow'] == True):
                fstr = 'UNFOLLOW'
            event = {'type':fstr, 'PublicKey':follower, 'Followed':followed}
        
        elif(transactionType == 'LIKE'):
            metadata = transaction['TransactionMetadata']
            transactor = metadata['TransactorPublicKeyBase58Check']
            posthash = metadata['LikeTxindexMetadata']['PostHashHex']
            isUnlike = metadata['LikeTxindexMetadata']['IsUnlike']
            poster = ''
            for k in metadata['AffectedPublicKeys']:
                if(k['Metadata'] == 'PosterPublicKeyBase58Check'):
                    poster = k['PublicKeyBase58Check']
            event = {'type':'LIKE', 'PublicKey':transactor, 'Post':posthash, 'Unlike':isUnlike, 'Poster':poster}

        if(len(event)> 0):
            print(event)

def dumpTopBlock():
    h = getChainHeight()
    block = getBlockInfo(h)
    print(json.dumps(block))

def getJsonFromFile(fname):
    # Opening JSON file
    f = open(fname,)
    data = json.load(f)
    return data

j = getJsonFromFile('block2.json')
processBlockJSON(j)

