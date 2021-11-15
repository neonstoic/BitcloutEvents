import json
import requests
import base58
import base64
from io import BytesIO
import time
from PIL import Image
from datetime import datetime
import math

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

def getProfilePhoto(pubkey):
    # Get profile picture for user id
    response = requests.get(endpoint+'/api/v0/get-single-profile-picture/'+pubkey)
    if response.status_code == 200:
        try:
            bo = BytesIO(response.content)
            bo.seek(0)
            piImage = Image.open(bo)
            piImage.resize((20, 20), Image.ANTIALIAS)    
            buf = BytesIO()
            piImage.save(buf, format="webp")
            imgStr = base64.b64encode(buf.getvalue())
            return str(imgStr)
        except:
            return ''
    return ''

    #print(imgStr)

def createProfileTexture(userMap):
    imageList = {}
    numWide = 20
    imWidth = 20
    imHeight = 20

    for k in userMap:

        response = requests.get(endpoint+'/api/v0/get-single-profile-picture/'+k)
        if response.status_code == 200:
            try:
                bo = BytesIO(response.content)
                bo.seek(0)
                piImage = Image.open(bo)
                piImage.thumbnail((imWidth, imHeight))
                imageList[k] = piImage
            except:
                False
    
    count = len(imageList)
    outWidth = imWidth*numWide
    outHeight = imHeight * math.trunc(count / numWide) + imHeight

    outImage = Image.new('RGB', (outWidth, outHeight))
    x = y = 0

    outUserPos = {}
    for k in imageList:
        outImage.paste(imageList[k], (x,y))
        outUserPos[k] = (x,y)
        x += imWidth
        if(x >= outWidth):
            x = 0
            y += imHeight
    outImage.save('out.webp')
    return outUserPos

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

def processBlockJSON(json, resolve=False, getProfilePics=False):
    transactions = json['Transactions']
    transactionCount = len(transactions)
    header = json['Header']
    height = header['Height']
    timestamp = header['TstampSecs']
    dt_object = datetime.fromtimestamp(timestamp)
    date_time = dt_object.strftime("%m/%d/%Y, %H:%M:%S")
    userKeyList = {}

    max = 0
    counter = 0

    processResp =  { 'Events':[] }

    for transaction in transactions:
        if(max != 0 and counter > max):
            break
        counter += 1
        transactionType = transaction['TransactionType']

        event = ''

        if(transactionType == 'BLOCK_REWARD'):
            outputs = transaction['TransactionMetadata']['AffectedPublicKeys'][0]
            k = outputs['PublicKeyBase58Check']
            a = transaction['TransactionMetadata']['TxnOutputs'][0]['AmountNanos']
            uname = uphoto = ''

            if(resolve):
                uname = getname(k)

            if not k in userKeyList:
                userKeyList[k] = {'Name':uname, 'Key':k, 'Photo':''}

            event = {'type':'BLOCK_REWARD', 'Name':uname, 'PublicKey':k, 'amount':a}

        elif(transactionType == 'FOLLOW'):
            affectedkeys = transaction['TransactionMetadata']['AffectedPublicKeys']
            follower = followed = ''
            followerName = followedName = ''
            for a in affectedkeys:
                if(a['Metadata'] == 'FollowedPublicKeyBase58Check'):
                    followed = a['PublicKeyBase58Check']
                    followedName = ''
                    if(resolve):
                        followedName = getname(followed)

                    if(not followed in userKeyList):
                        userKeyList[followed] = {'Name':followedName, 'Key':followed, 'Photo':uphoto}

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

            if(not poster in userKeyList):
                userKeyList[poster] = {'Name':posterName, 'Key':poster, 'Photo':''}

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
        
            uname = ''
            if(resolve):
                uname = event['Name'] = getname(posterhash)
                if(parentPosterHash != ''):
                    event['ReplyTo'] = getname(parentPosterHash)
            if(not posterhash in userKeyList):
                userKeyList[posterhash] = {'Name':uname, 'Photo':''}
                                  
        if(len(event)> 0):
            processResp['Events'].append(event)
    
    processResp['Profiles'] = []

    userImagePos = createProfileTexture(userKeyList)
    for k in userKeyList:
        item = userKeyList[k]
        if(k in userImagePos):
            item['x'] = userImagePos[k][0]
            item['y'] = userImagePos[k][1] 
        processResp['Profiles'].append(item)

    return processResp


def summarizeEvents(eventsJSON):
    likeDictionary = {}
    likeReceivedDictionary = {}

    summaryResp = {'Events':[]}
        
    for e in eventsJSON['Events']:
        if(e['type'] == 'LIKE'):
            n = e['Name']
            if(n in likeDictionary):
                likeDictionary[n] = likeDictionary[n] + 1
            else:
                likeDictionary[n] = 1

    for e in eventsJSON['Events']:     
        if(e['type'] == 'LIKE'):
            n = e['PosterName']
            if(n in likeReceivedDictionary):
                likeReceivedDictionary[n]['count'] += 1
                found = False
                for p in likeReceivedDictionary[n]['posts']:
                    if(p == e['Post']):
                        found = True;                    
                if(not found):
                    likeReceivedDictionary[n]['posts'].append(e['Post'])
            else:
                likeReceivedDictionary[n] = {'count':1, 'posts':[e['Post']]}
            
    for n in likeReceivedDictionary:
            summaryResp['Events'].append({'type':'LIKE_RECIEVED', 'Name':n, 'Count':likeReceivedDictionary[n]['count'], 'Posts':likeReceivedDictionary[n]['posts']})
    
    for n in likeDictionary:
        if(likeDictionary[n] > 20):
                summaryResp['Events'].append({'type':'LIKE', 'Name':n, 'Count':likeDictionary[n]})

    summaryResp['Profiles'] = eventsJSON['Profiles']
    return summaryResp


def dumpTopBlock():
    h = getChainHeight()
    block = getBlockInfo(h)
    print(json.dumps(block))

def getJsonFromFile(fname):
    # Opening JSON file
    f = open(fname,)
    data = json.load(f)
    return data

#j = getJsonFromFile('block2.json')
#resp = processBlockJSON(j, resolve=True, getProfilePics=True)
resp = getJsonFromFile('out.json')
resp = summarizeEvents(resp)
print(json.dumps(resp))