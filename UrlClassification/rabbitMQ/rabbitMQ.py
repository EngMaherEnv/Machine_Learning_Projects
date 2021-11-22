# -*- coding: utf-8 -*-
"""
Created on Thu Aug 12 08:32:43 2021

@author: STC
"""

import pika, sys, os
import mimetypes
from deep_translator import GoogleTranslator
import json
import pandas as pd
import pickle
from queue import Queue 
from threading import Thread
import time





class MyAnalysisThread (Thread):
   def __init__(self, comingQuary):
      Thread.__init__(self)
      self.comingQuary = comingQuary

   def run(self):
      analysis(self.comingQuary)




def sendToRabbit(linkFeatures):
    
      
      if linkFeatures['resultOfPrediction']:
          global sendChannelsuccess;
          sendChannelsuccess.basic_publish(exchange='', routing_key='success_Classification', body=json.dumps(linkFeatures, indent = 4) )
      else:
          global sendChannelfaild;
          sendChannelfaild.basic_publish(exchange='', routing_key='faild_Classification', body=json.dumps(linkFeatures, indent = 4) )
              
      print(" [x] send to  rabbitMQ %r" %  linkFeatures)
      print('////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////')

def analysis(comingQuary):
    
            print(" [x] Received from messageQueue at analysis in the created thread %r" %  comingQuary)
       
            baseUrl=comingQuary['Domain']
            href=comingQuary['Link']
            rel=comingQuary['Rel']
            title=comingQuary['Title']
            urlLength=len(href)
            titleLength=0
            if title is not None:
                titleLength=len(title)
                    
            nOfForwardSlash = href.count('/')
            nOfDot = href.count('.')
            nOfAnd = href.count('&')
            nOfEqual = href.count('=')
            nOfSemicolon = href.count(';')
            nOfPercent= href.count('%')
            nOfAt  = href.count('@')
            nOfHyphen = href.count('–')
            nOfUnderscore = href.count('_')
            nOfComma= href.count(',')
            nOfHash= href.count('#')
            # count numbers in title 
            nOfDdigits=0
            try:
                for i in title:
                    if(i.isdigit()):
                        nOfDdigits=nOfDdigits+1
            except:
                nOfDdigits=0
            #is the link is going to change our website
            otherWebsiteLink=False
            if baseUrl not in href:
                otherWebsiteLink=True
                
            #can i follow 
            follow_allowed=False
            if len(rel) == 0:
                follow_allowed=True
            
            #is it a file link lik jpg or zip 
            fileLink, _ = mimetypes.guess_type(href)
            isFileLink=False
            if fileLink is not None:
                isFileLink=True
                
            #is it  only base url 
            isBaseOnly=False
            if  baseUrl==href or href=='/' :
                 isBaseOnly=True
           
            #is the link contains any non important pages    
            containsNOfollowKeyword=False
            categorybysplit=''
            translatedCategoy=''
            NoFollowKeyword=['contact','contact us','login','log in','about us','about us','terms of use','privacy policy','cookie policy','terms and conditions','sign in','sign up','signin','signup','authors','membership','info','I forgot my password']
    
            try:
                if (otherWebsiteLink==False and isBaseOnly==False ):
                        categorybysplit=href.split(baseUrl)[1:]
                        toBeTranslate=categorybysplit[0]+title
                        translatedCategoy= GoogleTranslator(source='auto', target='en').translate(toBeTranslate)
                        if any(word in translatedCategoy.lower() for word in NoFollowKeyword):
                                containsNOfollowKeyword=True
            except:
                translatedCategoy='no words'
                
            isNews=False
            if(isBaseOnly==False and isFileLink==False and  follow_allowed==True  and otherWebsiteLink==False and containsNOfollowKeyword==False):
                    isNews=True
                             
            global InputsPanda;
            Row = InputsPanda.append({'otherWebsiteLink' :otherWebsiteLink, 'follow_allowed':follow_allowed,'isFileLink':isFileLink, 'isBaseOnly' : isBaseOnly, 'containsNOfollowKeyword' : containsNOfollowKeyword, 'urlLength' : urlLength, 'titleLength' : titleLength, 'nOfDdigits' : nOfDdigits, 'nOfForwardSlash' : nOfForwardSlash, 'nOfDot' : nOfDot, 'nOfEqual' : nOfEqual, 'nOfHash' : nOfHash,}, 
                    ignore_index = True)
            resultOfPrediction=UrlClassModel.predict(Row)
            #channge to bool
            FinalResult=0
            if resultOfPrediction[0]:
                FinalResult = True
            else:
                FinalResult = False
            
            print(resultOfPrediction[0])
            
            linkFeatures={
                    'resultOfPrediction':FinalResult,
                    'domain':baseUrl,
                    'href':href,
                    'otherWebsiteLink':otherWebsiteLink,
                    'follow_allowed':follow_allowed,
                    'isFileLink':isFileLink,
                    'isBaseOnly':isBaseOnly,
                    'containsNOfollowKeyword':containsNOfollowKeyword,
                    'rel':rel,
                    'title':title,
                    'urlLength':urlLength,
                    'titleLength':titleLength,
                    'nOfDdigits':nOfDdigits,
                    'nOfForwardSlash':nOfForwardSlash,
                    'nOfDot':nOfDot,
                    'nOfAnd':nOfAnd,
                    'nOfEqual':nOfEqual,
                    'nOfSemicolon':nOfSemicolon,
                    'nOfPercent':nOfPercent,
                    'nOfAt':nOfAt,
                    'nOfHyphen':nOfHyphen,
                    'nOfUnderscore':nOfUnderscore,
                    'nOfComma':nOfComma,
                    'nOfHash':nOfHash,
                    'fileLink':fileLink
                    }
            

            sendToRabbit(linkFeatures)


     
      

def analysisCall(messageQueue, consumerClose):
       print('//////////////////////////// analysis started')
       while True: 
        if(messageQueue.empty()==False):
            
            #get the message 
            comingQuary=messageQueue.get()
            messageQueue.task_done()
            
            analysisThread = MyAnalysisThread ( comingQuary)
            analysisThread.start()
            analysisThread.join()

            
        elif(consumerClose.empty()==False):
                # when the consumer is stopped go out the loop
                if(consumerClose.get()==True):
                    print('consumer stopped')
                    break;
        else:
            print('sleeping for .....1')
            # wait some n sec  before next iteration
            time.sleep(1)
            
       
        
   
def consumeFromRabbit(messageQueue, consumerClose):
    
    credentials = pika.PlainCredentials('crawler', '123456sS')
    
    connection = pika.BlockingConnection( pika.ConnectionParameters('192.168.2.217',5672,'/',credentials))
    channel = connection.channel()
    


    def callback(ch, method, properties, body):
        comingQuary=json.loads(body)
        # print( "[x] Received from rabbitMq  at consumeFromRabbit  %r" %  comingQuary)
        messageQueue.put(comingQuary)
        
       
        

    channel.basic_consume(queue='links', on_message_callback=callback, auto_ack=False)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming() 
    
    consumerClose.put(True)
    print("consumer stopped")    

        
def main():
    print('this is main')
    
    #create shared ques: 
        
    messageQueue = Queue()
    consumerClose=Queue()
    
    consumerThread = Thread(target = consumeFromRabbit, args =(messageQueue, consumerClose))
    analysisThreadCall = Thread(target = analysisCall, args =(messageQueue,consumerClose ))
    
    consumerThread.start()
    analysisThreadCall.start()
    
    consumerThread.join() 
    analysisThreadCall.join() 
    
    
    
    


if __name__ == '__main__':
    
    InputsPanda = pd.DataFrame(columns = [ 'otherWebsiteLink', 'follow_allowed', 'isFileLink','isBaseOnly','containsNOfollowKeyword','urlLength','titleLength','nOfDdigits','nOfForwardSlash','nOfDot','nOfEqual','nOfHash'])
    
    filename = 'urlClassification_model.sav'
    UrlClassModel = pickle.load(open(filename, 'rb'))
    
    credentials = pika.PlainCredentials('/////', '/////')
    Sendconnectionsuccess = pika.BlockingConnection(pika.ConnectionParameters('//////',////,'/',credentials))
    Sendconnectionfaild = pika.BlockingConnection(pika.ConnectionParameters('///////',////,'/',credentials))

    sendChannelsuccess = Sendconnectionsuccess.channel()
    sendChannelfaild = Sendconnectionfaild.channel()

    
    sendChannelsuccess.queue_declare(queue='success_Classification')
    sendChannelfaild.queue_declare(queue='faild_Classification')
    
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
            
            
           
