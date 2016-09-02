import websocket
import time
import sys
import json
import hashlib
import zlib
import base64
import threading
from datetime import datetime
from stock import stock,KLine,Trade
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S'
                    )
pricelogging = logging.getLogger("price")
pricelogging.addHandler(logging.FileHandler("price.log"))

tradelogging = logging.getLogger("trade")
tradelogging.addHandler(logging.FileHandler("trade.log"))



api_key='25b3b6dc-5834-4a9f-aaec-fce834c8db89'
secret_key = "DBFB0BE60D46ECC3EC907AA8F786E513"

last_time=0;
ws=None
tradeIndex={}
tradeLastTime = None
bidsList=[]
asksList=[]


stock1Min = stock("btc_cny",stock.OneMin,500)
stock5Min = stock("btc_cny",stock.FiveMin,500)
stock15Sec = stock("btc_cny",stock.FifteenSec,500)
stock15Min = stock("btc_cny",stock.FifteenMin,500)

buyPrice = None
buyPrice1 = None
buyPrice2 = None
buy1Time = None
buy2Time = None
buyTriggerTime = None
buyPrice3=None
downToUp = None
upToDown = None
middleToUp = None
spec =None
xspec = None
sellSpec = None
xbuy = None
xkdj = None

#business
def buildMySign(params,secretKey):
    sign = ''
    for key in sorted(params.keys()):
        sign += key + '=' + str(params[key]) +'&'
    return  hashlib.md5((sign+'secret_key='+secretKey).encode("utf-8")).hexdigest().upper()

def on_open(self):
    #subscribe okcoin.com spot ticker
    #self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_ticker','binary':'true'}")
    self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_trades','binary':'true'}")
    self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_depth_60','binary':'true'}")
    stock1Min = stock("btc_cny",stock.OneMin,500)
    stock5Min = stock("btc_cny",stock.FiveMin,500)
    stock15Sec = stock("btc_cny",stock.FifteenSec,500)
    stock15Min = stock("btc_cny",stock.FifteenMin,500)

    self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_kline_1min','binary':'true'}")
    self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_kline_5min','binary':'true'}")
    #self.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_kline_15min','binary':'true'}")


def go():
    global buyPrice1,buyPrice2,bidsList,asksList,buy1Time,buy2Time,buyTriggerTime,buyPrice3,downToUp,upToDown,middleToUp,spec,xspec,sellSpec,xbuy,xkdj
    m5up,m5down,m5next = stock5Min.forecastClose()
    m1up,m1down,m1next = stock1Min.forecastClose()
    lastM5 = stock5Min.lastKline()
    prelastM5 = stock5Min.preLastKline()
    pre2lastM5 = stock5Min.pre2LastKline()
    current = stock1Min.lastKline()
    lastm1 = stock1Min.preLastKline()
    prelastm1 = stock1Min.pre2LastKline()
    lastM15 = stock15Min.lastKline()

    #if len(bidsList)<=1:
    #    return

    #m1upSellSupport = findTotalSupportWithAsks(m1up,asksList[0])
    #m1upBuySupport = findTotalSupportWithBids(m1up,bidsList[0])

    #m5upSellSupport = findTotalSupportWithAsks(m5up,asksList[0])
    #m5upBuySupport = findTotalSupportWithBids(m5up,bidsList[0])

    if current.time-lastM5.time>=5*60:
        return

    #pricelogging.info("time=%s,msup=%s,ssup=%s,price=%s,M5 up=%s,down=%s,next=%s,%s,boll=%s,m5close=%s" % (time.ctime(current.time),m5upBuySupport,m5upSellSupport,current.close,m5up,m5down,m5next,stock5Min.forecastKDJ(),lastM5.boll,lastM5.close))
    #pricelogging.info("time=%s,msup=%s,ssup=%s,price=%s,M1 up=%s,down=%s,next=%s,%s" % (time.ctime(current.time),m1upBuySupport,m1upSellSupport,current.close,m1up,m1down,m1next,stock1Min.forecastKDJ()))

    pricelogging.info("time=%s,price=%s,touchShortDown=%s,buyprice=%s,1jkd=%s,pre1kdj=%s,buy1time=%s,cukdj=%s" % (time.ctime(current.time),current.close,stock1Min.touchShortDown(),buyPrice1,lastm1.j-lastm1.k,prelastm1.j-prelastm1.k,buy1Time,current.j-current.k))


    prelast5diff = prelastM5.j-prelastM5.k
    pre2last5diff = pre2lastM5.j - pre2lastM5.k

    prelast1diff = lastm1.j-lastm1.k
    pre2last1diff = prelastm1.j - prelastm1.k

    pricelogging.info("spec=%s,5down=%s,pre2kdj=%s,prekdj=%s,curkdj=%s" % (spec,stock5Min.touchDownRange(0,4),pre2last5diff,prelast5diff,lastM5.j-lastM5.k))

    if spec == None:
        if buy1Time==None and stock5Min.touchDownRange(0,4)==True \
                                and pre2last5diff<-5 and prelast5diff>0 and prelast5diff>pre2last5diff:
            buy1Time = current.time
            buy2Time = lastM5.time
            xkdj = prelast1diff
            xbuy="11"
            spec = 1
            pricelogging.info("xbuy11-%s,%s,time=%s,b2time=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(buy1Time),time.ctime(buy2Time)))

        if buy1Time==None and stock5Min.touchDownRange(0,4)==True \
                and pre2last5diff>0 and prelast5diff>0 and prelast5diff>pre2last5diff:
            buy1Time = current.time
            buy2Time = lastM5.time
            xkdj = prelast1diff
            xbuy="12"
            spec = 1
            pricelogging.info("xbuy12-%s,%s,time=%s,b2time=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(buy1Time),time.ctime(buy2Time)))

        #touch down to up
        if buy1Time==None and stock5Min.touchDownRange(0,4)==True and \
                                stock5Min.preMyLastKline(3).j- stock5Min.preMyLastKline(3).k < 0 and pre2last5diff<-5 and prelast5diff>-5 and prelast5diff>pre2last5diff:
            buy1Time = current.time
            buy2Time = lastM5.time
            xkdj = prelast1diff
            xbuy="1"
            spec = 1
            pricelogging.info("xbuy1-%s,%s,time=%s,b2time=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(buy1Time),time.ctime(buy2Time)))


    '''
    #touch middle to up
    if buy1Time==None and stock5Min.touchMiddle()==True and stock5Min.touchHighBetweenMiddleRange()==True and stock5Min.touchMiddleToLowRange()==False and \
                            stock5Min.preMyLastKline(3).j- stock5Min.preMyLastKline(3).k < 0 and pre2last5diff<-5 and prelast5diff>-5 and prelast5diff>pre2last5diff:
        buy1Time = current.time
        buy2Time = lastM5.time
        xkdj = prelast1diff
        xbuy="2"
        spec = 1
        pricelogging.info("xbuy2-%s,%s,time=%s,b2time=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(buy1Time),time.ctime(buy2Time)))

    #touch down middle to up
    if buy1Time==None and stock5Min.touchMiddle()==True and stock5Min.touchMiddleToLowRange() and stock5Min.touchHighBetweenMiddleRange()==True and \
                            stock5Min.preMyLastKline(3).j- stock5Min.preMyLastKline(3).k < 0 and pre2last5diff<-5 and prelast5diff>-5 and prelast5diff>pre2last5diff:
        buy1Time = current.time
        buy2Time = lastM5.time
        xkdj = prelast1diff
        xbuy="3"
        spec = 1
        pricelogging.info("xbuy3-%s,%s,time=%s,b2time=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(buy1Time),time.ctime(buy2Time)))
    '''

    if buy2Time!=None and lastM5.time - buy2Time == 5*60 and (prelast5diff<pre2last5diff or prelast5diff<0):
        if buyPrice1 > current.close:
            return
        if buyPrice1!=None:
            pricelogging.info("tbuy4-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))

        pricelogging.info("disable-%s-%s,time=%s,deciderTime=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
        buy1Time = None
        buy2Time = None
        xbuy=None
        buyPrice1 = None
        xkdj = None
        spec = None


    if buy1Time!=None and buyPrice1==None and xbuy!=None and spec==1:
        if stock1Min.downToUp() and xkdj<0:
            if (pre2last1diff<0 and prelast1diff>0) or (pre2last1diff>=0 and prelast1diff>pre2last1diff):
                pricelogging.info("tbuy12-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
                buyPrice1 = current.close
                xkdj = None
                spec = 2
            return

        if stock1Min.downToUp() and stock1Min.countCross(buy1Time)==0 and stock1Min.kdjUpDontTouchMax(buy1Time) and lastM5.j-lastM5.k>prelast5diff:
            pricelogging.info("tbuy10-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
            buyPrice1 = current.close
            xkdj = None
            spec = 2
            return

        if stock1Min.downToUp() and stock1Min.kdjUp(buy1Time) and stock1Min.kdjUpDontTouchMax(buy1Time) and lastM5.j-lastM5.k>prelast5diff:
            pricelogging.info("tbuy1-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
            buyPrice1 = current.close
            xkdj = None
            spec = 2
            return
        if stock1Min.downToUp()==False and prelast1diff<0 and current.close<current.boll and lastM5.j-lastM5.k>prelast5diff:
            pricelogging.info("tbuy2-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
            buyPrice1 = current.close
            xkdj = None
            spec = 2
            return

        if stock1Min.downToUp()==False and pre2last1diff<0 and prelast1diff>pre2last1diff and current.close>current.boll and lastM5.j-lastM5.k>prelast5diff:
            pricelogging.info("tbuy21-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
            buyPrice1 = current.close
            xkdj = None
            spec = 2
            return

        if stock1Min.downToUp() and stock1Min.kdjUp(buy1Time) and stock1Min.kdjUpDontTouchMax(buy1Time)==False and prelast1diff>pre2last1diff and lastM5.j-lastM5.k>prelast5diff:
            pricelogging.info("tbuy3-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
            buyPrice1 = current.close
            xkdj = None
            spec = 2
            return

    if buy2Time!=None and  lastM5.time - buy2Time > 5*60 and lastM5.j-lastM5.k<=0:
        if buyPrice1 > current.close:
            return
        if buyPrice1!=None:
            pricelogging.info("tbuy5-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        pricelogging.info("disable2-%s-%s,time=%s,deciderTime=%s" % (xbuy,stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
        buy1Time = None
        buy2Time = None
        xbuy=None
        buyPrice1 = None
        xkdj = None
        spec=None


    if buyPrice1!=None and spec==2 and ((stock1Min.countTouchUp(buy1Time)>=1 and stock1Min.countCross(buy1Time)>2) or stock1Min.countTouchUp(buy1Time)==1)and stock1Min.touchUpSell():
        if stock1Min.lastKline().close > buyPrice1:
            pricelogging.info("tbuy6-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
            buy1Time = None
            xbuy=None
            buyPrice1 = None
            xkdj = None
            spec = 3


    if buyPrice1!=None and spec==3 and prelast1diff < pre2last1diff and stock1Min.touchUpMyShort():
        if stock1Min.lastKline().close > buyPrice1:
            pricelogging.info("tbuy7-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
            buy1Time = None
            xbuy=None
            buyPrice1 = None
            xkdj = None

    if buyPrice1==None and spec==3 and buy2Time!=None and prelast1diff > pre2last1diff and  pre2last1diff<0 and prelast1diff>0 and prelast5diff>0 and lastM5.j-lastM5.k>0 and lastM5.j-lastM5.k>prelast5diff:
        pricelogging.info("tbuy8-%s,time=%s,deciderTime=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),time.ctime(buy1Time)))
        buyPrice1=current.close
        buy1Time = current.time

    '''
    if buyPrice1==None and prelast5diff<0 and pre2last5diff<0 and  prelast5diff>pre2last5diff and prelast5diff>-5 and stock5Min.touchShortDown() \
        and stock1Min.touchDown() and stock1Min.downToUp():
        if pre2last1diff<0 and prelast1diff>=0 :
            pricelogging.info("tbuy-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            spec = True
        if pre2last1diff>=0 and prelast1diff > pre2last1diff:
            pricelogging.info("tbuy1-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            spec = True

    if buyPrice1==None and prelast5diff<0 and pre2last5diff<0 and  prelast5diff>pre2last5diff and prelast5diff>-5 and stock5Min.touchSimlarDown(4) \
            and stock1Min.touchDown() and stock1Min.downToUp():
        if pre2last1diff<0 and prelast1diff>=0 :
            pricelogging.info("tbuy21-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            spec = True
        if pre2last1diff>=0 and prelast1diff > pre2last1diff:
            pricelogging.info("tbuy22-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            spec = True


    if buyPrice1!=None and spec==True and prelast5diff>0:
        spec = None

    if buyPrice1!=None and spec==True and buy1Time!=current.time and prelast1diff < pre2last1diff and stock1Min.touchMiddleLong()==False and buy1Time-lastM5.time<5*60:
        pricelogging.info("tbuy2-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        spec = None
        xbuy = None

    if buyPrice1!=None and spec==None and buy1Time!=current.time and stock1Min.touchUpSell():
        pricelogging.info("tbuy4-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        spec = None
        xbuy = None

    if (xbuy=="6" or xbuy=="9") and  buyPrice1!=None and spec==None and buy1Time!=current.time and prelast1diff<0 and prelast1diff<pre2last1diff and not (stock5Min.middleUpByIndex(0) and lastM5.j - lastM5.k> 0):
        pricelogging.info("tbuy5-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        spec = None
        xbuy = None


    if (xbuy=="7" or xbuy=="8") and  buyPrice1!=None and spec==None and buy1Time!=current.time and buy1Time-lastM5.time<0 and prelast1diff<0 and prelast1diff<pre2last1diff and not (stock5Min.middleUpByIndex(0) and lastM5.j - lastM5.k> 0):
        pricelogging.info("tbuy5-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        spec = None
        xbuy = None

    if buyPrice1==None and spec==None and stock1Min.touchDown() and prelast5diff>0 and lastM5.j - lastM5.k>5 and lastM5.j-lastM5.k > prelast5diff and lastm1.j - lastm1.k>=0 and prelastm1.j-prelastm1.k<0:
        pricelogging.info("tbuy6-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        xbuy = "6"

    if buyPrice1==None and spec==None and stock5Min.middleUpByIndex(1) and stock5Min.middleUpByIndex(0) and lastM5.j - lastM5.k> 5 and stock1Min.downToUp()==False and stock5Min.downToUp()==True:
        if stock1Min.touchMiddle():
            pricelogging.info("tbuy7-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            xbuy="7"
        elif prelast1diff>0 and pre2last1diff<0:
            pricelogging.info("tbuy8-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = current.close
            buy1Time = current.time
            xbuy="8"
    if buyPrice1==None and spec==None and prelast1diff>0 and prelast1diff> pre2last1diff and current.j-current.k > prelast1diff and stock1Min.forecastKDJ()==True and lastM5.j-lastM5.k>5 and prelast5diff>0 and lastM5.j-lastM5.k > prelast5diff and stock5Min.downToUp() and stock1Min.downToUp():
        pricelogging.info("tbuy9-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        xbuy = "9"

    '''

    '''
    if sellSpec and ((current.time == buy1Time and current.close>buyPrice1) or (current.time!=buy1Time)):
        pricelogging.info("tbuy21-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = None
        middleToUp = None
        spec = None
        xspec = None
        sellSpec = None

    if buyPrice1==None and stock1Min.touchShortDown() and lastm1.j - lastm1.k>=0 and prelastm1.j-prelastm1.k<0:
        pricelogging.info("tbuy-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        downToUp=True
        upToDown=None
        middleToUp = None
        spec = None
        xspec = None

    fn = lambda: lastm1.j-lastm1.k<0 and current.j - current.k>0 and current.close > m1down \
                 and current.close > m1up and current.close > m1next and m1upBuySupport>40 and not stock5Min.touchDown()

    if buyPrice1==None and stock1Min.touchShortDown() and fn():
        pricelogging.info("tbuy8-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        downToUp=True
        upToDown=None
        middleToUp = None
        spec = None
        xspec = True


    if buyPrice1==None and stock5Min.downToUp() and fn() and (stock1Min.downToUp() or stock1Min.touchMiddleLong()):
        pricelogging.info("tbuy9-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        downToUp=True
        upToDown=None
        middleToUp = None
        spec = True
        xspec = None

    if (xspec or spec) and buyPrice1!=None and buy1Time==current.time and current.close<buyPrice1:
        sellSpec = True


    if buyPrice1!=None and buy1Time!=current.time and lastm1.j-lastm1.k<=0 and current.j-current.k<0 and downToUp==True and (not stock1Min.touchUp()):
        if prelastM5.close>prelastM5.open and prelastM5.close > pre2lastM5.close:
            return
        else:
            pricelogging.info("tbuy1-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
            buyPrice1 = None
            buy1Time = None
            downToUp = None
            upToDown = None
            middleToUp = None
            spec = None
            xspec = None

    if buy1Time!=current.time and buyPrice1!=None and lastm1.j-lastm1.k<=0 and downToUp==True and stock1Min.touchUp() or (buy1Time!=current.time and buyPrice1!=None and lastm1.close<lastm1.open and middleToUp==True and stock1Min.touchUp()):
        pricelogging.info("tbuy2-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = True
        middleToUp = None
        spec = None
        xspec = None


    if buyPrice1==None and stock5Min.middleUpByIndex(0) and  lastM5.j - lastM5.k> 0 and stock1Min.downToUp()==False and \
            (stock1Min.touchMiddle() or lastm1.j-lastm1.k > 0):
        pricelogging.info("tbuy3-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = current.close
        buy1Time = current.time
        middleToUp=True
        upToDown = None
        downToUp = None
        spec = None
        xspec = None


    if buyPrice1!=None and middleToUp and stock1Min.touchShortDown() and not (stock5Min.touchDown() and prelastM5.j-prelastM5.k>0):
        pricelogging.info("tbuy4-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = None
        middleToUp = None
        spec = None
        xspec = None


    fndown = lambda: lastm1.j-lastm1.k>0 and current.j - current.k<0 and current.close < m1down \
                 and current.close < m1up and current.close < m1next and m1upSellSupport>30

    if buyPrice1!=None and spec and buy1Time!=current.time and fndown():
        pricelogging.info("tbuy7-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = None
        middleToUp = None
        spec = None
        xspec = None

    if buyPrice1!=None and xspec and buy1Time!=current.time and  current.time - buy1Time <= 60*3 and stock1Min.mayDown():
        pricelogging.info("tbuy12-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = None
        middleToUp = None
        spec = None
        xspec = None


    if buyPrice1 != None and buy1Time!=current.time and buyPrice1 > current.close + 5:
        pricelogging.info("tbuy5-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),time.ctime(stock1Min.lastKline().time)))
        buyPrice1 = None
        buy1Time = None
        downToUp = None
        upToDown = None
        middleToUp = None
        spec = None
        xspec = None



    '''
    '''
    if lastm1.j-lastm1.k <0 and isbuy==True and current.close > m1up and buyPrice1==None:
        pricelogging.info("tbuy-%s,time=%s" % (stock1Min.lastKline().close,stock1Min.lastKline().time))
        buyPrice1 = current.close

    if buyPrice1!=None and issell==True and current.close < m1up:
        pricelogging.info("tbuy-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
        buyPrice1 = None
    '''


    '''
    kdj,touchBoll = stock1Min.canBuy()

    pricelogging.info("5j-5k=%s,%s,5m=%s,%s,%s,%s,%s,%s,%s,%s" % (lastM5.j-lastM5.k,(prelastM5.j-prelastM5.k<0 and lastM5.j-lastM5.k<5),stock5Min.premiddleDown(),lastm1.j-lastm1.k>prelastm1.j-prelastm1.k,
                                                            touchBoll,lastm1.close> prelastm1.close,current.close>lastm1.close,current.close > m1up,current.close > m1next,buyTriggerTime) )

    if ((lastM5.j-lastM5.k<0 and prelastM5.j-prelastM5.k<-5) or (prelastM5.j-prelastM5.k<0 and lastM5.j-lastM5.k<5) )  and stock5Min.premiddleDown() and lastm1.j-lastm1.k>prelastm1.j-prelastm1.k \
            and touchBoll==True and lastm1.close> prelastm1.close and current.close>lastm1.close and current.close > m1up and current.close > m1next \
        and buyPrice1==None and buyTriggerTime==None:
        buyTriggerTime = current.time
        pricelogging.info("tbuy-trigger,time=%s,price=%s" % (time.ctime(current.time),current.close))

    if buyPrice1 == None:
        if buyTriggerTime != None and current.time - buyTriggerTime == 120:
            if current.j- current.k >= lastm1.j-lastm1.k and not (prelastM5.j-prelastM5.k>=0 and lastM5.j - lastM5.k<=0):
                pricelogging.info("tbuy-%s,time=%s,t=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time),buyTriggerTime))
                buyPrice1 = current.close
                buyPrice3 = current.close
                buy1Time = lastM5.time
                buyTriggerTime = None
            else:
                pricelogging.info("tbuy-destory-trigger,time=%s,price=%s,triggerTime=%s" % (time.ctime(current.time),current.close,buyTriggerTime))
                buyTriggerTime = None
        elif buyTriggerTime != None and current.time - buyTriggerTime > 120:
            pricelogging.info("tbuy-destory-trigger,time=%s,price=%s,triggerTime=%s" % (time.ctime(current.time),current.close,buyTriggerTime))
            buyTriggerTime = None

    if buyPrice1 != None and buyPrice1 > current.close + 5:
        if not (prelastM5.j-prelastM5.k>-2 and lastM5.j-lastM5.k>0) or buyPrice1 > current.close + 10:
            pricelogging.info("tbuy1-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
            buyPrice1 = None
            buy1Time = None
            buy2Time = None


    touchUp = stock1Min.touchUp();
    if buyPrice1!=None and touchUp == True and lastM5.j - lastM5.k<=0:
        pricelogging.info("tbuy2-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
        buyPrice1 = None
        buy1Time = None
        buy2Time = None
        if buyPrice3!=None:
            pricelogging.info("tbuy8-%s,sell-%s,diff=%s,time=%s" % (buyPrice3,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice3),stock1Min.lastKline().time))
            buyPrice3 = None

    if buyPrice1!=None:
        pricelogging.info("txtime=%s,%s,%s" % (buyPrice1,buy2Time,prelastM5.j-prelastM5.k))
        pricelogging.info("txtime2=%s,%s,%s" % (buyPrice1,buy2Time,lastM5.j - lastM5.k))

    if buyPrice1!=None and buy2Time==None and prelastM5.j-prelastM5.k>=0:
        buy2Time = lastM5.time

    if buyPrice1!=None and buy2Time!=None and lastM5.j - lastM5.k<=0:
        pricelogging.info("tbuy3-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
        buyPrice1 = None
        buy1Time = None
        buy2Time = None

        if buyPrice3!=None:
            pricelogging.info("tbuy6-%s,sell-%s,diff=%s,time=%s" % (buyPrice3,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice3),stock1Min.lastKline().time))
            buyPrice3 = None

    if buyPrice3!=None and stock1Min.touchUpShort() and lastm1.open > lastm1.close and current.close > buyPrice3:
        pricelogging.info("tbuy5-%s,sell-%s,diff=%s,time=%s" % (buyPrice3,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice3),stock1Min.lastKline().time))
        buyPrice3 = None
        if stock5Min.touchUpMyShort()==True and buyPrice1!=None:
            pricelogging.info("tbuy9-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
            buyPrice1 = None
            buy1Time = None
            buy2Time = None
            downToUp = True



    if buyPrice1!=None and buyPrice3==None and stock1Min.touchMiddle()==True and lastM5.j-lastM5.k>10:
        buyPrice3 = current.close
        pricelogging.info("tbuy7-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))

    if downToUp == True and buyPrice3==None and stock1Min.touchDown() and lastM5.j-lastM5.k>10:
        buyPrice3 = current.close
        pricelogging.info("tbuy11-%s,time=%s" % (stock1Min.lastKline().close,time.ctime(stock1Min.lastKline().time)))


    if downToUp == True and buyPrice3!=None and (lastM5.j-lastM5.k<=0 or (stock1Min.touchUpShort() and lastm1.open > lastm1.close and current.close > buyPrice3)):
        pricelogging.info("tbuy12-%s,sell-%s,diff=%s,time=%s" % (buyPrice3,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice3),stock1Min.lastKline().time))
        buyPrice3 = None

    if downToUp==True and buyPrice3==None and lastM5.j-lastM5.k <=0:
        downToUp = False
    '''

    '''
    if buy1Time!=None and buyPrice1!=None:
        if lastM5.time - buy1Time <= 5*60:
            if lastm1.j-lastm1.k<0 and current.close<m1up :
                pricelogging.info("tbuy1-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
                buyPrice1 = None
                buy1Time = None
            if lastm1.j-lastm1.k>0 and current.close<m1up:
                if int(current.close)>=int(m5up):
                    return
                pricelogging.info("tbuy2-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
                buyPrice1 = None
                buy1Time = None
        else:
            buy1Time = None
    '''
    '''
        if current.close<m5up and lastM5.j-lastM5.k>0 and buy2Time==None:
            buy2Time = lastM5.time
        elif buy2Time!=None and current.time-buy2Time>3 and current.close<m5up and lastm1.j-lastm1.k<prelastm1.j-prelastm1.k:
            pricelogging.info("tbuy3-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
            buyPrice1 = None
            buy2Time = None
        elif buy2Time!=None and current.time-buy2Time>4 and prelastM5.j-pre2lastM5.k > pre2lastM5.j-pre2lastM5.k:
            buy2Time = None
        elif buy2Time!=None and current.time-buy2Time>4 and prelastM5.j-pre2lastM5.k < pre2lastM5.j-pre2lastM5.k:
            pricelogging.info("tbuy4-%s,sell-%s,diff=%s,time=%s" % (buyPrice1,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice1),stock1Min.lastKline().time))
            buyPrice1 = None
            buy2Time = None
        '''

    '''
    kdj,touchBoll = stock1Min.canBuy()
    if buyPrice2!=None and kdj==False:
        pricelogging.info("buy2-%s,sell-%s,diff=%s" % (buyPrice2,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice2)))
        buyPrice2 = None
    if buyPrice2==None and kdj==True and stock5Min.forecastKDJ()==True:
        buyPrice2=stock1Min.lastKline().close
        pricelogging.info("buy2-%s,time=%s" % (stock1Min.lastKline().close,stock1Min.lastKline().time))
    '''

def on_message(self,evt):
    global last_time
    global buyPrice
    global tradeIndex
    global tradeLastTime
    global bidsList,asksList
    data = inflate(evt) #data decompress
    mjson = json.loads(data)

    if type(mjson) == dict and mjson.has_key("event") and mjson["event"]=="pong":
        last_time = time.time()
        return
    if type(mjson) == list:
        for tdata in mjson:
            if tdata.has_key("channel") and tdata["channel"] == "ok_sub_spotcny_btc_kline_1min" and tdata.has_key("data"):
                kdata = tdata["data"]
                if type(kdata[0]) == int :
                    stock1Min.on_kline(KLine(kdata))
                else:
                    for k in kdata:
                        stock1Min.on_kline(KLine(k))
                kdj,touchBoll = stock1Min.canBuy()
                pricelogging.info("kdj=%s,touch=%s,fiveIsStrong=%s" % (kdj,touchBoll,stock5Min.isUp()))

                if buyPrice!=None and kdj==False:
                    pricelogging.info("buy-%s,sell-%s,diff=%s" % (buyPrice,stock1Min.lastKline().close,(stock1Min.lastKline().close-buyPrice)))
                    buyPrice = None
                if buyPrice==None and kdj==True and touchBoll==True:
                    buyPrice=stock1Min.lastKline().close
                    pricelogging.info("buy-%s,time=%s,boll" % (stock1Min.lastKline().close,stock1Min.lastKline().time))
                if buyPrice==None and kdj==True and touchBoll==False and stock5Min.isUp()==True:
                    buyPrice=stock1Min.lastKline().close
                    pricelogging.info("buy-%s,time=%s" % (stock1Min.lastKline().close,stock1Min.lastKline().time))
                go()
            if tdata.has_key("channel") and tdata["channel"] == "ok_sub_spotcny_btc_kline_5min" and tdata.has_key("data"):
                kdata = tdata["data"]
                if type(kdata[0]) == int :
                    stock5Min.on_kline(KLine(kdata))
                else:
                    for k in kdata:
                        stock5Min.on_kline(KLine(k))
                go()
            if tdata.has_key("channel") and tdata["channel"] == "ok_sub_spotcny_btc_kline_15min" and tdata.has_key("data"):
                kdata = tdata["data"]
                if type(kdata[0]) == int :
                    stock15Min.on_kline(KLine(kdata))
                else:
                    for k in kdata:
                        stock15Min.on_kline(KLine(k))
                go()

            if tdata.has_key("channel") and tdata["channel"] == "ok_sub_spotcny_btc_trades" and tdata.has_key("data"):
                kdata = tdata["data"]
                for k in kdata:
                    td = Trade(k)
                    stock15Sec.tkine(td)
                    '''
                    if tradeIndex.has_key(str(td.time)) == False:
                        tradeIndex[str(td.time)] = td.vol
                        if tradeLastTime == None:
                            tradeLastTime = str(td.time)
                        else:
                            logging.info("Trade=" + str(tradeIndex[tradeLastTime]))
                            tradeLastTime = str(td.time)
                    else:
                        tradeIndex[str(td.time)] = td.vol +  tradeIndex[str(td.time)]
                    '''

            if tdata.has_key("channel") and tdata["channel"] == "ok_sub_spotcny_btc_depth_60" and tdata.has_key("data"):
                bidsList.insert(0,tdata["data"]["bids"])
                asksList.insert(0,tdata["data"]["asks"])

                if len(bidsList)>=6:
                    bidsList.pop()
                if len(asksList)>=6:
                    asksList.pop()


def findTotalSupportWithBids(price,data):
    ret = 0;
    for d,v in data:
        if d>=price:
           ret = ret + v
    return ret;

def findTotalSupportWithAsks(price,data):
    ret = 0
    for d,v in data:
        if d<=price:
            ret = ret +v
    return ret

def findMaxSupport(data):
    for d,v in data:
        if v>20 :
            return d,v

    ret = None
    for d,v in data:
        if ret==None:
            ret = (d,v)
        elif ret[1]<v:
            ret = (d,v)
    return ret

def canBuyWithBids(cur,old):
    curd,curv = findMaxSupport(cur)
    oldd,oldv = findMaxSupport(old)

    pricelogging.info("curd=%s,curv=%s,old=%s,oldv=%s" % (curd,curv,oldd,oldv))

    if curd > oldd:
        return True
    elif curd == oldd and curv+20 < oldv:
        return False
    elif curd == oldd and curv>= oldv + 20:
        return True
    elif curd<oldd:
        return False
    else:
        return None

def canBuyWithAsks(cur,old):
    curd,curv = findMaxSupport(cur)
    oldd,oldv = findMaxSupport(old)

    pricelogging.info("asks ,curd=%s,curv=%s,old=%s,oldv=%s" % (curd,curv,oldd,oldv))
    if curd > oldd:
        return True
    elif curd == oldd and curv+20 < oldv:
        return True
    elif curd == oldd and curv>=oldv+20:
        return False
    elif curd<oldd:
        return False
    else:
        return None


def inflate(data):
    decompress = zlib.decompressobj(
            -zlib.MAX_WBITS  # see above
    )
    inflated = decompress.decompress(data)
    inflated += decompress.flush()
    return inflated

def on_error(self,evt):
    print (evt)

def on_close(self,evt):
    print ('DISCONNECT')

def on_pong(self,evt):
    self.send("{'event':'ping'}")

def connect():
    global ws;
    url = "wss://real.okcoin.cn:10440/websocket/okcoinapi"
    websocket.enableTrace(True)
    if len(sys.argv) < 2:
        host = url
    else:
        host = sys.argv[1]
    ws = websocket.WebSocketApp(host,
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.on_pong = on_pong

    ws.run_forever(ping_interval=3)

def check_connect():
    event = threading.Event()
    while not event.wait(6):
        #print(time.time() - last_time)
        if last_time == 0:
            continue;
        if time.time()-last_time>6:
            ws.close()

'''
if __name__ == "__main__":
    thread = threading.Thread(target=check_connect)
    thread.setDaemon(True)
    thread.start()

    while True:
        try:
            connect();
            stock1Min = stock("btc_cny",stock.OneMin,500)
            stock5Min = stock("btc_cny",stock.FiveMin,500)
            stock15Sec = stock("btc_cny",stock.FifteenSec,500)
            stock15Min = stock("btc_cny",stock.FifteenMin,500)
            print("reconnect")
        except Exception,e:
            logging.error(e)

'''
