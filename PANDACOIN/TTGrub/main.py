import requests, time, json, random, threading, datetime
import yaml
global addresses
global refresh
global recent
global comp
global conf
config = yaml.load(open('config.yaml').read(), Loader=yaml.FullLoader) #Reading Config
addresses = config['Address']
refresh = config['Timer']
recent = config['Recent']
comp = config['Compensate']
conf = config['Confirmations']

def txCheck(txid, unix, amount, address):
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

def txConfirm(txid, conf):
    txInfo = requests.get('https://ravencoin.network/api/tx/'+txid).json()
    if txInfo['confirmations'] >= conf:
        return True
    else:
        return False
    
def paymentCheck(invoice, address, amount):
    done=False
    tranConfirmed=False
    unix = int(time.time())
    knownTx = []
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
            invoice['Paid'] = True
            invoice['Address'] = payer
            invoice['Amount'] = str(amount)
            invoice['Time'] = datetime.datetime.utcfromtimestamp(unix).strftime('%Y-%m-%d %H:%M:%S')
            return True
def main():
    offer = str(input("Assets on offer: "))
    price = float(input("Price [RVN] "))
    address = random.choice(addresses)
    print("Address to pay: "+address)
    payment = {"Paid": False}
    paid = False
    threading.Thread(target=paymentCheck, args=(payment, address, price,), daemon=True).start()
    while paid == False:
        if payment['Paid']:
            print('Invoice Paid')
            paid = True
    if paid:
        msg = payment['Address']+','+payment['Amount']+','+offer+','+payment['Time']+','
        with open('payments.csv','a') as p:
            p.write(msg+'\n')
        with open(str(payment['Amount'])+'.csv','a') as a:
            a.write(msg+'\n')


if __name__ == "__main__":

    while True:
        main()
