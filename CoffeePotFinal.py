import picamera
from time import sleep
import pygame
import random
import time
from PIL import Image
import numpy
import cv2
import matplotlib.pyplot as plt
import smtplib
import os,sys
#TWITTER USR: cpsc353gp PSWD: ai_coffeepot
import tweepy
import random
plt.rcParams['backend'] = 'Qt4Agg'

WIDTH=1280   
HEIGHT=960

# INIT CAMERA
camera = picamera.PiCamera()
camera.resolution = (WIDTH, HEIGHT)

camera.vflip = True
camera.hflip = True
camera.brightness = 60

coffeeLevel = 0.0

def takePhoto():
        camera.capture('coffee.jpg', format='jpeg')

#set small box over the black and decker label to assure it is in the range we check
def setupCamera():
        camera.start_preview()
        imgOverlay = Image.open('box.png')


        pad = Image.new("RGB", (
            WIDTH,
            HEIGHT
            ))

        pad.paste(imgOverlay, (0,0), imgOverlay)

        o=camera.add_overlay(pad.tostring(), size = (1280,960))
        o.alpha = 100
        o.layer = 3
        input('Setup Camera and press enter when ready')
        camera.remove_overlay(o)
        camera.stop_preview()
        


#detector
def isCoffee(path):
        img = cv2.imread(path,0)
        imgCopy = cv2.imread(path,0)

        xCoords = []
        yCoords = []
        fillLevel = []
        #get all of the lines found in the image
        edges = cv2.Canny(img,50,150)
        lines = cv2.HoughLinesP(edges, 1, numpy.pi/2, 6, None, 50, 10);
        horizontalLinePoints = []
        coffeeLevel = 0
        checkPoints = []

        if (lines is None):
                print("Can't find pot")
                return False
        #get all coordinates of lines
        for i in range (0,len(lines)):

                x1 = lines[i][0][0]
                x2 = lines[i][0][2]
                y1 = lines[i][0][1]
                y2 = lines[i][0][3]
                #if the line has a slope less than .5, treat it as horizontal
                if (x2-x1 != 0 and (y2-y1)/(x2-x1) < 0.5):
                        cv2.line(img, (x1,y1), (x2,y2), (0,0,255), 2)
                        horizontalLinePoints.append([x1,y1,x2,y2])
        #dont really need this loop at all, but im too scared to change anything
        for j in horizontalLinePoints:
                checkPoints.append([j[0],j[2],j[1]])

        potentialPoints = []
        #go through the lines we've found, if theyre within the range we expect the
        #label to be in, then add them to the list
        for j in checkPoints:
                for k in checkPoints:
                        if j[0] > 715 and k[0] > 715 and j[0] < 825 and k[0] < 825 and j[2] > 520 and k[2] > 520 and j[2] < 580 and k[2] < 580:
                                potentialPoints.append(j)
                                cv2.line(imgCopy,(j[0],j[2]),(j[1],j[2]),(0,0,255),2)

        topOfLabel = 1000
        bottomOfLabel = 0
        tempRight = 0
        #out of all the lines in the box, get the top most one and the bottom most one to determine height of label
        #once we have this, there is a constant relationship between the size of label and the rest of the features
        for i in potentialPoints:
                
                if i[2] < topOfLabel:
                        topOfLabel = i[2]
                        tempRight = i[1]
                if i[2] > bottomOfLabel:
                        bottomOfLabel = i[2]
        #this is what we will use to determine how to find relevant features of coffee pot
        goldenLength = bottomOfLabel - topOfLabel
        topOfPot = topOfLabel - goldenLength*11
        bottomOfPot = topOfLabel + goldenLength*3
        rightSide = tempRight + goldenLength * 3
        leftSide = rightSide - goldenLength * 12
        #draw box around coffee pot, and determine height of the pot so that the fill
        #level can be determined. it is a rough estimation so it is probably accurate in a range of
        # +/- 10 %
        cv2.line(imgCopy,(leftSide,topOfPot),(leftSide,bottomOfPot),(0,0,255),2)
        cv2.line(imgCopy,(rightSide,topOfPot),(rightSide,bottomOfPot),(0,0,255),2)
        cv2.line(imgCopy,(leftSide,bottomOfPot),(rightSide,bottomOfPot),(0,0,255),2)
        cv2.line(imgCopy,(leftSide,topOfPot),(rightSide,topOfPot),(0,0,255),2)

        finalPoints = []
        #once the box is created, find all lines inside it, these are the potential coffee levels
        for x1,x2,y in checkPoints:
                if x1 > leftSide and x2 < rightSide and y > topOfPot and y < bottomOfPot and [x1,x2,y] not in potentialPoints:
                        finalPoints.append([x1,x2,y])
        if len(finalPoints) == 0:
                print ('The coffee pot is empty')
                coffeeLevel = 0.0
                return False

        elif len(finalPoints) > 0:
                #if weve found something, determine if the color below the line is black and the color above is white
                #if so, this is probably the coffee line.
                for i in finalPoints:
                        if imgCopy[i[2] + 20 ,i[0]+ (i[1]-i[0])/2] <100 and imgCopy[i[2] - 20 ,i[0]+ (i[1]-i[0])/2] > 100:
                                cv2.line(imgCopy,(i[0],i[2]),(i[1],i[2]),(0,0,255),2)
                                height = (bottomOfPot* 1.0) - topOfPot
                                fullness = (bottomOfPot-i[2])/height
                                print ('coffee pot is ' , fullness*100, 'percent full')
                                coffeeLevel = fullness*100
                                return True

        print ('The coffee pot is empty')
        coffeeLevel = 0.0
        return False
#then send an email out informing user of coffee situation
def sendEmail(coffeeStatus):
    msg = ''
    if coffeeStatus == True:
        msg = 'There is coffee!'
    else:
        msg = 'Coffee pot is empty. You know what to do.'
    

    server = smtplib.SMTP('smtp.gmail.com',587) #port 465 or 587
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('annikahudak96@gmail.com','chapman12')
    server.sendmail('annikahudak96@gmail.com','hudak101@mail.chapman.edu',msg)
    server.close()
    
def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)
#and a tweet
def sendTweet(status):
  cfg = { 
    "consumer_key"        : "lwRGV5F4XsMl9gnZfd2kQEoV9",
    "consumer_secret"     : "iSEBBao3vyUjnlNHA2KLyPl3Xe0DxVYVNEgp8qdEE7sOu3dPd8",
    "access_token"        : "4286716820-eupPYWE9AYWBvIXf5aVAYWgfagb2SdeNw6em29r",
    "access_token_secret" : "AZXnED4XIbNdNz3HdZyIgVnJ6NcNtvQ00EzfHbQv058Ld" 
    }
  randomFacts = ['Donald Trump abstains from caffeine, which means you should not.',
                 'How did the hipster burn his tongue? He sipped his coffee before it was cool.',
                 '#muglife', '#ilovecoffee','#fitfam #fitstyle #fitsperation #fitexpo #imfit #lifestyle',
                 'espresso yourself <3','Ima let you finish, but Aussie Bean had some of the best coffee of all time.',
                 'PROCAFFEINATING (n.) the tendency to not start anything until you have had a coffee.',
                 'Java? I prefer espresso.', 'If a fraternity opens a coffee shop they would specialize in frataccino.',
                 'If someone hits you over the head with a coffee cup, have you been mugged?',
                 'What do you call a cow that just gave birth? Decaffeinated.', 'If you were ground coffee, you would be Espresso cause you are so fine.',
                 'Drinking too much coffee can cause a latte problems.', '#caffeine #lol'
                 ]
  coffeeReady = ['YAY coffee!', 'COFFEEEEEEEE!','drink me!','Caffeine now!', 'It'"'"'s a BREWtiful morning!','Livin la vida mocha :)',
                 'HEEEYYYY SEXXY LATTE!', 'We were meant to bean.','Heading to my happy place.', 'L-O-V-E what'"'"'s that spell? COFFEE!',
                 'The thought of coffee makes me stir.', 'Better latte than never!']
  coffeeNotReady = ['...there is no coffee.', 'SOS coffee gone!','no coffee :(','Where'"'"'s all the coffee? We were mugged!!',
                    'How do you feel when there is no coffee? Depresso.', 'The struggle is real.', 'Coffee...prepare to meet your maker.',
                    'Need. More. Coffee.','Coffee pot half full or half empty?? JK all empty, fill me up bish.','Ding dong the coffee'"'"'s gone.'
                    ]
  coffeeStatus = 'I dunno'
  coffeePun = 'depresso'
  if status == True:
      coffeePun = coffeeReady
      coffeeStatus = 'There is coffee.'
  else:
      coffeePun = coffeeNotReady
      coffeeStatus = 'There is no coffee.'

  api = get_api(cfg)
  tweet = coffeeStatus + random.choice(coffeePun) + ' ' + random.choice(randomFacts)
  if(len(tweet) >139):
          tweet = coffeeStatus

  loop = True
  while (loop):
          try:
              status = api.update_status(status=tweet)
              loop = False
          except:
                loop = True
                tweet = coffeeStatus + random.choice(coffeePun) + ' ' + random.choice(randomFacts)
              
                        
setupCamera()
#if the first thing returned is true, then start checking every 10 seconds
#however since false negatives are common, if empty is returned then check 10 times, and if you find at least
#2 potential coffee levels ( potential is if they are within 10% coffee level of eachother), then the pot is full
while (True):
        takePhoto()
        coffeeBool = isCoffee('coffee.jpg')
        if (coffeeBool):
                sendEmail(coffeeBool)
                sendTweet(coffeeBool)
                print('email sent')
                print('tweet sent')
                print(' ')

        if not coffeeBool:
                print('Checking further...')
                
                i=0
                levelArr = []
                while (i < 10):
                        print('secondary check ', i)
                        takePhoto()
                        b = isCoffee('coffee.jpg')
                        if (b):
                                levelArr.append(coffeeLevel)
                        i += 1
                        
                        
                if (len(levelArr) > 1 ):
                        closeSum = 0
                        for i in levelArr:
                                for j in levelArr:
                                        if (abs(i-j) < 10):
                                                closeSum += 1
                        closePercentage = closeSum/(2*len(levelArr))
                        print ('close percentage', closePercentage)
                        if (closePercentage > 0.5):
                                
                                sendEmail(True)
                                sendTweet(True)
                                print('THERE IS COFFEE!')
                                print('email sent')
                                print('tweet sent')
                                print(' ')
                else:
                        sendEmail(False)
                        sendTweet(False)
                        print('THERE IS NO COFFEE')
                        print('email sent')
                        print('tweet sent')
                        print(' ')
                             
        print ('waiting..')
        sleep(10)
        








