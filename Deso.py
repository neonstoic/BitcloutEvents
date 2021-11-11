import json
import requests
import base58
import time
from datetime import datetime

#endpoint = 'https://api.bitclout.com'
endpoint = 'http://127.0.0.1:17001'
nameMap = {}

def getChainHeight():
    response = requests.post(endpoint+'/api/v0/get-app-state', json={ "PublicKeyBase58Check":"BC1YLint2QNJWyNMX8kAiiTiYjT8yrTNYtzXKbGhXRoj7dPyNHboQLY"})
    respdata = json.loads(response.text)
    chainheight = respdata['BlockHeight']
    return chainheight

def getBlockInfo(height):
    # Call /api/v1/block to get details about a block passed to the function
    data = { 'Height':height, 'FullBlock':True }
    print(data)
    #response = requests.post(endpoint+"/api/v1/block", json=data)
    response = requests.post('https://api.bitclout.com/api/v1/block', json=data)
    # Return the JSON response
    respdata = json.loads(response.text)
    return respdata

    #counter = 0
    #while True :
    #    try :


def getname(hash):
    if(hash in nameMap):
        return nameMap[hash]

    data = {'PublicKeyBase58Check':hash}
    response = requests.post(endpoint+"/api/v0/get-single-profile", json=data)
    respdata = {}

    if response.status_code == 200:
        respdata = json.loads(response.text)
        name = respdata['Profile']['Username']        
    else:
        name = ''

    nameMap[hash] = name
    return name    

def processBlockJSON(json, resolve=False):
    transactions = json['Transactions']
    transactionCount = len(transactions)
    header = json['Header']
    height = header['Height']
    timestamp = header['TstampSecs']
    dt_object = datetime.fromtimestamp(timestamp)
    date_time = dt_object.strftime("%m/%d/%Y, %H:%M:%S")
    
    processResp =  { 'Events':[] }

    for transaction in transactions:
        transactionType = transaction['TransactionType']

        event = ''

        if(transactionType == 'BLOCK_REWARD'):
            outputs = transaction['TransactionMetadata']['AffectedPublicKeys'][0]
            k = outputs['PublicKeyBase58Check']
            a = transaction['TransactionMetadata']['TxnOutputs'][0]['AmountNanos']
            uname = ''
            if(resolve):
                uname = getname(k)
            event = {'type':'BLOCK_REWARD', 'Name':uname, 'PublicKey':k, 'amount':a}

        elif(transactionType == 'FOLLOW'):
            affectedkeys = transaction['TransactionMetadata']['AffectedPublicKeys']
            follower = followed = ''
            followerName = followedName = ''
            for a in affectedkeys:
                if(a['Metadata'] == 'FollowedPublicKeyBase58Check'):
                    followed = a['PublicKeyBase58Check']
                    if(resolve):
                        followedName = getname(followed)
                elif(a['Metadata'] == 'BasicTransferOutput'):
                    follower = a['PublicKeyBase58Check']
                    if(resolve):
                        followerName = getname(follower)
            fstr = 'FOLLOW'
            if(transaction['TransactionMetadata']['FollowTxindexMetadata']['IsUnfollow'] == True):
                fstr = 'UNFOLLOW'
            event = {'type':fstr, 'Name':followerName, 'PublicKey':follower, 'FollowedName':followedName, 'FollowedKey':followed}
        
        elif(transactionType == 'LIKE'):
            metadata = transaction['TransactionMetadata']
            transactor = metadata['TransactorPublicKeyBase58Check']
            transactorName = ''
            
            posthash = metadata['LikeTxindexMetadata']['PostHashHex']
            isUnlike = metadata['LikeTxindexMetadata']['IsUnlike']
            poster = ''
            posterName = ''
            for k in metadata['AffectedPublicKeys']:
                if(k['Metadata'] == 'PosterPublicKeyBase58Check'):
                    poster = k['PublicKeyBase58Check']
            
            if(resolve):
                transactorName = getname(transactor)
                posterName = getname(poster)

            event = {'type':'LIKE', 'Name':transactorName, 'PublicKey':transactor, 'Post':posthash, 'Unlike':isUnlike, 'PosterName':posterName, 'Poster':poster}

        elif(transactionType == 'SUBMIT_POST'):
            metadata = transaction['TransactionMetadata']
            affectedpubkeys = metadata['AffectedPublicKeys']
            mentoinedList = []
            posterhash = parentPosterHash = postHash = ''
            for k in affectedkeys:
                if(k['Metadata'] == 'BasicTransferoutput'):
                    posterhash = k['PublicKeyBase58Check']
                elif(k['Metadata'] == 'ParentPosterPublicKeyBase58Check'):
                    parentPosterHash = k['PublicKeyBase58Check']
                elif(k['Metadata'] == 'MentionedPublicKeyBase58Check'):
                    mentoinedList.push(k['PublicKeyBase58Check'])
            postHash = metadata['SubmitPostTxindexMetadata']['PostHashBeingModifiedHex']

            event = {'type':'POST', 'Name':'', 'PublicKey':posterhash, 'Post':postHash, 'ReplyToPK':parentPosterHash, 'ReplyTo':''}
        
            if(resolve):
                event['Name'] = getname(posterhash)
                if(parentPosterHash != ''):
                    event['ReplyTo'] = getname(parentPosterHash)
                    
              
        if(len(event)> 0):
            processResp['Events'].append(event)
            #print(event)
    
    return processResp

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
resp = processBlockJSON(j, resolve=True)
print(json.dumps(resp))
