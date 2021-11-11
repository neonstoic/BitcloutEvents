import time
import Deso

top = 0

while True:
    newtop = Deso.getChainHeight()
    if newtop > top:        
        print('new top found: ', newtop)
        top = newtop
        time.sleep(5)
        block = Deso.getBlockInfo(top)
        Deso.processBlockJSON(block, resolve=True)
    else:
        print(".", end='')
    time.sleep(15.0)