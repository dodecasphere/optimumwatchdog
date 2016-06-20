import os
import sys
import time
from datetime import datetime
import threading
import twitter
import json
import random
from logger import Logger
import re

working_dir = os.path.dirname(os.path.realpath(__file__)) + '/'

def main(filename, argv):
    print "======================================"
    print " Starting Speed Complainer!           "
    print " Lets get noisy!                      "
    print "======================================"

    global working_dir

    monitor = Monitor()
    monitor.run()

class Monitor():
    def __init__(self):
        self.lastPingCheck = None
        self.lastSpeedTest = None

    def run(self):
        if not self.lastPingCheck or (datetime.now() - self.lastPingCheck).total_seconds() >= 60:
            self.runPingTest()
            self.lastPingCheck = datetime.now()

        if not self.lastSpeedTest or (datetime.now() - self.lastSpeedTest).total_seconds() >= 3600:
            self.runSpeedTest()
            self.lastSpeedTest = datetime.now()

    def runPingTest(self):
        pingThread = PingTest()
        pingThread.start()

    def runSpeedTest(self):
        speedThread = SpeedTest()
        speedThread.start()

class PingTest(threading.Thread):
    def __init__(self, numPings=3, pingTimeout=2, maxWaitTime=6):
        super(PingTest, self).__init__()
        self.numPings = numPings
        self.pingTimeout = pingTimeout
        self.maxWaitTime = maxWaitTime
        self.config = json.load(open(working_dir + 'private_config.json'))
        self.logger = Logger(self.config['log']['type'], { 'filename': working_dir + self.config['log']['files']['ping'] })

    def run(self):
        pingResults = self.doPingTest()
        self.logPingResults(pingResults)

    def doPingTest(self):
        response = os.system("ping -c %s -W %s -w %s 8.8.8.8 > /dev/null 2>&1" % (self.numPings, (self.pingTimeout * 1000), self.maxWaitTime))
        success = 0
        if response == 0:
            success = 1
        return { 'date': datetime.now(), 'success': success }

    def logPingResults(self, pingResults):
        self.logger.log([ pingResults['date'].strftime('%Y-%m-%d %H:%M:%S'), str(pingResults['success'])])

class SpeedTest(threading.Thread):
    def __init__(self):
        super(SpeedTest, self).__init__()
        self.config = json.load(open(working_dir + 'private_config.json'))
        self.logger = Logger(self.config['log']['type'], { 'filename': working_dir + self.config['log']['files']['speed'] })

    def run(self):
        speedTestResults = self.doSpeedTest()
        self.logSpeedTestResults(speedTestResults)
        self.tweetResults(speedTestResults)

    def doSpeedTest(self):
        # run a speed test
        result = os.popen("speedtest-cli --simple --share").read()
        if 'Cannot' in result:
            return { 'date': datetime.now(), 'uploadResult': 0, 'downloadResult': 0, 'ping': 0 }

        # Result:
        # Ping: 529.084 ms
        # Download: 0.52 Mbit/s
        # Upload: 1.79 Mbit/s

        resultSet = result.split('\n')
        pingResult = resultSet[0]
        downloadResult = resultSet[1]
        uploadResult = resultSet[2]
        shareImage = resultSet[3]

        print pingResult
        print downloadResult
        print uploadResult
        print shareImage

        # pingResult = float(pingResult.replace('Ping: ', '').replace(' ms', ''))
        # downloadResult = float(downloadResult.replace('Download: ', '').replace(' Mbit/s', ''))
        # uploadResult = float(uploadResult.replace('Upload: ', '').replace(' Mbit/s', ''))

        pingResult = float(re.findall("\d+\.\d+", pingResult)[0])
        downloadResult = float(re.findall("\d+\.\d+", downloadResult)[0])
        uploadResult = float(re.findall("\d+\.\d+", uploadResult)[0])
        shareImage = shareImage[13:]

        return {
            'date': datetime.now(),
            'uploadResult': uploadResult,
            'downloadResult': downloadResult,
            'ping': pingResult,
            'imageUrl': shareImage }

    def logSpeedTestResults(self, speedTestResults):
        self.logger.log([ speedTestResults['date'].strftime('%Y-%m-%d %H:%M:%S'),
                        str(speedTestResults['uploadResult']),
                        str(speedTestResults['downloadResult']),
                        str(speedTestResults['ping']) ])


    def tweetResults(self, speedTestResults):
        thresholdMessages = self.config['tweetThresholds']
        message = None
        for (threshold, messages) in thresholdMessages.items():
            threshold = float(threshold)
            if speedTestResults['downloadResult'] < threshold:
                message = messages[random.randint(0, len(messages) - 1)] \
                    .replace('{tweetTo}', self.config['tweetTo']) \
                    .replace('{internetSpeed}', self.config['internetSpeed']) \
                    .replace('{downloadResult}', str(speedTestResults['downloadResult'])) \
                    .replace('{imageUrl}', str(speedTestResults['imageUrl']))

        print "Composing tweet!"
        print ">>> " + message
        print "..."

        if message:
            api = twitter.Api(consumer_key=self.config['twitter']['twitterConsumerKey'],
                            consumer_secret=self.config['twitter']['twitterConsumerSecret'],
                            access_token_key=self.config['twitter']['twitterToken'],
                            access_token_secret=self.config['twitter']['twitterTokenSecret'])
            if api:
                status = api.PostUpdate(message)

        print "Tweeted!"

if __name__ == '__main__':
    main(__file__, sys.argv[1:])

    sys.exit(0)



