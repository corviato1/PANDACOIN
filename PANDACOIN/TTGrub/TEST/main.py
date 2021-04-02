import requests, time, json, random, threading, datetime, string
import yaml
from flask import Flask, render_template, request
##global addresses
global refresh
global recent
global comp
global conf
global invoices
global config
##global invoiceId
app=Flask(__name__)
config = yaml.load(open('config.yaml').read(), Loader=yaml.FullLoader) #Reading Config
##addresses = config['Address']
refresh = config['Timer']
recent = config['Recent']
comp = config['Compensate']
conf = config['Confirmations']
invoices=[]
##invoiceId=0
def rand(str_size, allowed_chars):
    return ''.join(random.choice(allowed_chars) for x in range(str_size))

def txCheck(txid, unix, amount, address):
    try:
        txInfo = requests.get('https://ravencoin.network/api/tx/'+txid).json()
        if txInfo['time'] > unix:
            d = False
            for output in txInfo['vout']:
                if address in output['scriptPubKey']['addresses']:
                    d=float(output['value'])
            if d == False:
                return False
            cAmount = float(amount - comp)
            dAmount = float(amount + comp)
            if cAmount < d < dAmount:
                return txInfo
            else:
                return False
        else:
            return False
    except:
        pass
    return False
def txConfirm(txid, conf):
    txInfo = requests.get('https://ravencoin.network/api/tx/'+txid).json()
    if txInfo['confirmations'] >= conf:
        return True
    else:
        return False
    
def paymentCheck(ids, address, amount):
    print('checking for '+str(ids)+' on '+address)
    done=False
    tranConfirmed=False
    unix = int(time.time())
    knownTx = []
##    invoice = lst[ids]
    while done == False:
        current = requests.get('https://ravencoin.network/api/addr/'+address).json()
        
        txToCheck = []
        for tx in range(recent):
            txToCheck.append(current['transactions'][tx])

        for txid in knownTx:
            if txid in txToCheck:
                txToCheck.remove(txid)

        for txid in txToCheck:
            resp = txCheck(txid, unix, amount, address)
            if resp:
                print('Payment of '+str(amount)+' was detected to '+address+' [UNCONFIRMED] {'+str(txid)+'}')
                payer = resp['vin'][0]['addr']
                pTx = txid
                done = True
        time.sleep(refresh)
    while tranConfirmed == False:
        while txConfirm(pTx, conf) == False:
            time.sleep(refresh)
        if txConfirm(pTx, conf):
            print('Payment of '+str(amount)+' was paid to '+address+' [CONFIRMED] {'+str(pTx)+'}')
            tranConfirmed=True
            invoices[ids]['Paid'] = True
            invoices[ids]['Time'] = datetime.datetime.utcfromtimestamp(unix).strftime('%Y-%m-%d %H:%M:%S')
            return True
##def main():
##    offer = str(input("Assets on offer: "))
##    price = float(input("Price [RVN] "))
##    address = random.choice(addresses)
##    print("Address to pay: "+address)
##    payment = {"Paid": False}
##    paid = False
##    threading.Thread(target=paymentCheck, args=(payment, address, price,), daemon=True).start()
##    while paid == False:
##        if payment['Paid']:
##            print('Invoice Paid')
##            paid = True
##    if paid:
##        msg = payment['Address']+','+payment['Amount']+','+offer+','+payment['Time']+','
##        with open('payments.csv','a') as p:
##            p.write(msg+'\n')
##        with open(str(payment['Amount'])+'.csv','a') as a:
##            a.write(msg+'\n')
def getAddys():
    tosend="\""
    addresses = open('addy.txt').read().splitlines()
    for item in addresses:
        tosend+=item+"\", \""
    tosend=tosend[:-3]
##@app.route('/')
##def root():
##    addresses = open('addy.txt').read().splitlines()
##    addres=random.choice(addresses)
##    asss = getAddys()
##    return render_template('invoice.html', address=addres, addys=asss)

@app.route('/api')
def api():
    assetAmount = request.args.get('d')
    assetName = request.args.get('e')
    rvnAmount = request.args.get('f')
    rvnAddress = request.args.get('g')
##    print(assetAmount)
##    print(assetName)
##    print(rvnAmount)
    info = assetAmount+" "+assetName
    invId = rand(8, '0123456789abcdef')
    invoi = {"Paid": False, "ID": invId, "Address": rvnAddress, "Amount": rvnAmount, "Info": info}
    invoices.append(invoi)
    invoiceId = int(open('inv.txt').read())
    threading.Thread(target=paymentCheck, args=(invoiceId, rvnAddress, float(rvnAmount),), daemon=True).start()
    with open('inv.txt','w') as trac:
        trac.write(str(invoiceId+1))
    return ''

@app.route('/track')
def track():
    toreturn="<div>Tracking:</div>"
    for item in invoices:
        if item['Paid']:
            msg = item['ID']+" | PAID "+item['Address']+" ["+item['Amount']+"] "+item['Info']+" - "+ item['Time']
        else:
            msg = item['ID']+" | UNPAID "+item['Address']+" ["+item['Amount']+"] "+item['Info']
        toreturn+=msg+"...."
    toreturn = toreturn[:-4]
    return toreturn

@app.route('/asset')
def asset():
    addresses = open('addy.txt').read().splitlines()
    addres=random.choice(addresses)
    asss = getAddys()
    assetName = request.args.get('asset')
    try:
        price = str(config[assetName])
        js = requests.get('https://explorer-api.ravenland.org/asset?asset='+assetName).json()
        if js['hasIpfs']:
            ipfs = js['ipfsHash']
        else:
            ipfs = ''
        return render_template('visit.html', asset=assetName, price=price, ipfs=ipfs, address=addres, addys=asss)
    except:
        return '<h1>Unavailable</h1>'        

@app.route('/')
def listAssets():
##    configs = yaml.load(open('config.yaml').read(), Loader=yaml.FullLoader)
    tosend='<h1>Cool Panel</h1>'
    for item in config['Assets']:
        tosend+= '<br><a href="/asset?asset='+item+'">'+item+'</a><br />'
    return tosend
    
if __name__ == "__main__":
    with open('inv.txt','w') as te:
        te.write('0')
    app.run()
