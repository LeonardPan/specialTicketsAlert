# ! -*- coding: utf-8 -*- 

import urllib2
import random
import re
import threading
import json
import types
import ctypes
import MySQLdb
from datetime import datetime
import time

class specialTicketsConfig(object):
    interval = 60  # seconds
    baseUrl = 'http://ws.qunar.com/all_lp.jcp'
    fromCity = u'昆明'
    toCity = u'杭州'
    goDate = '2013-08-25'
    backDate = '2013-09-03'
    userAgents = ['Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0', \
         'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0', \
         'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533+ \
         (KHTML, like Gecko) Element Browser 5.0', \
         'IBM WebExplorer /v0.94', 'Galaxy/1.0 [en] (Mac OS X 10.5.6; U; en)', \
         'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)', \
         'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14', \
         'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) \
         Version/6.0 Mobile/10A5355d Safari/8536.25', \
         'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) \
         Chrome/28.0.1468.0 Safari/537.36', \
         'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0; TheWorld)']
    dbConfig = {
        'host':'localhost',
        'port':3306,
        'user':'root',
        'passwd':'admin',
        'db':'tickets'}
    
    def __init__(self):
        self.url = ("%s?from=%s&to=%s&goDate=%s&backDate=%s&count=%d&packto=%s&packreturn=%s&packcount=%d" 
                    "&output=json&n=0.013591776369139552&callback=jsonParser" 
                    % (self.baseUrl, self.fromCity, self.toCity, self.goDate, self.backDate, 90, self.goDate, self.backDate, 7))

class specialTicketsApp(object):
    lowestPrices = {}
    
    class ticketsCrawlThread(threading.Thread):
        @staticmethod
        def convertJsonArrary2List(inJson):
            return []
        
        def _getResultParsed(self, inRst):
            parsedResult = {}
            results = re.match("([a-z|A-Z]+)\((\{.*\})\);*", inRst)
            jsonStr = None
            if results is not None:
                (funName, jsonStr) = results.groups()
            try:
                jsonResult = json.loads(jsonStr)
            except Exception as e:
                print e
                return None
            if jsonResult.has_key('out') and type(jsonResult['out']) is types.DictType:
                for k, v in jsonResult['out'].iteritems():
                    date = re.match('2013-0([8|9])-([0-9]+)\|(\D+)-(\D+)', k)
                    if date is not None and date.group(3) == self.config.fromCity and date.group(4) == self.config.toCity:
                        month = int(date.group(1))
                        day = int(date.group(2))
                        if(month == 8 and day >= 25 and day <= 31) or (month == 9 and day >= 1 and day <= 5):
                            parsedResult[k] = v['pr'];
            return parsedResult
        
        def __init__(self, config):
            self.config = config
            threading.Thread.__init__(self)
            
        def _getForgedRequest(self):
            req = urllib2.Request(self.config.url.encode('utf-8'))
            index = random.randint(0, 9)
            userAgent = self.config.userAgents[index]
            req.add_header('User-agent', userAgent)
            return req 
        
        def _popAMessage(self, ttl, msg):
            MessageBox = ctypes.windll.user32.MessageBoxA
            MessageBox(None, msg.encode('utf-8'), ttl.encode('utf-8') , 0)
    
        def _alertLowestPrice(self, prices):
            for date, price in prices.iteritems():
                if not specialTicketsApp.lowestPrices.has_key(date):
                    specialTicketsApp.lowestPrices[date] = price
                elif int(price) < int(specialTicketsApp.lowestPrices[date]):
                    specialTicketsApp.lowestPrices[date] = price
                    message = 'until now, the lowest price for the date \n%s is: \n￥%s' % (date, price)
                    title = 'special ticket shows up!'
                    threading.Timer(0.5, self._popAMessage, [title, message]).start()
                    
        def _sendToDb(self, prices):
            sql = "INSERT INTO priceRecords (date, price, ts) VALUES ('%s', %s, NOW())"
            for date, price in prices.iteritems():
                try:
                    conn = MySQLdb.connect(host=self.config.dbConfig['host'],
                                           port=self.config.dbConfig['port'],
                                           user=self.config.dbConfig['user'],
                                           passwd=self.config.dbConfig['passwd'],
                                           db=self.config.dbConfig['db'],
                                           charset='utf8')
                    cursor = conn.cursor()
                    cursor.execute(sql % (date, price))
                    cursor.close()
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print "sent to db failed because of %s." % e
            
        def run(self):
            responce = urllib2.urlopen(self._getForgedRequest())
            result = responce.read()
            ticketsPrices = self._getResultParsed(result)
            self._alertLowestPrice(ticketsPrices)
            self._sendToDb(ticketsPrices)
    
    def __init__(self):
        self.config = specialTicketsConfig()
        
    def _process(self):
        tickCrawThread = self.ticketsCrawlThread(self.config)
        tickCrawThread.start()
        threading.Timer(self.config.interval, self._process).start()
        
    def _heatbeat(self):
        print str(datetime.now())
        threading.Timer(600, self._heatbeat).start()
        
    def start(self):
        print "begin the crawl loop:"
        threading.Timer(self.config.interval, self._process).start()
        threading.Timer(0, self._heatbeat).start()
        while True:
            time.sleep(0.1)

if __name__ == '__main__':
    specTicktsApp = specialTicketsApp()
    specTicktsApp.start()
