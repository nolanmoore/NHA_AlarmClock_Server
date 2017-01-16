# file NHA_AlarmClock_v2.py

from Adafruit_IO import *
import time
from datetime import datetime
from datetime import timedelta
import sys
import pygame.mixer as mixer
import urllib2
from HTMLParser import HTMLParser
import json
from twilio.rest import TwilioRestClient
import os
import logging.config

def setup_logging(
    default_path='logging.json',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration"""
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def playAlarm():
    """Plays alarm sound clip"""

    mixer.music.load('alarm.wav')
    mixer.music.play(9)
    return

def stopAlarm():
    """Stops alarm sound clip if currently playing"""

    if mixer.music.get_busy():
        mixer.music.stop()
    return

def playPong():
    """Plays chime sound clip"""
    if alarm['ringing'] == 'OFF':
        mixer.music.load('chime.wav')
        mixer.music.play()
    return

def getQOD():
    """Gets Quote of Day (QOD) from quotesondesign.com and uses Twilio
    service to text it to a predefined number"""

    qod_url = 'http://quotesondesign.com/api/3.0/api-3.0.json'
    response = urllib2.urlopen(qod_url).read()
    qod = json.loads(response)
    message = twilio_client.messages.create(to=MY_NUMBER, from_=TWILIO_NUMBER, body='\n{0}\n- {1}'.format(strip_tags(qod['quote']), qod['author']))
    return

def connected(client):
    """Callback function that sets up feed subscriptions"""

    logger.info('Connected to Adafruit IO')
    client.subscribe('alarm-set')
    client.subscribe('alarm-time')
    client.subscribe('alarm-server-ping')
    client.subscribe('alarm-snooze-poke')

def disconnected(client):
    """Callback function that merely prints a disconnect notification"""

    logger.info('Disconnected from Adafruit IO, reconnecting...')

    while not client.is_connected():
        try:
            client.connect()
        except:
            logger.info('Unable to connect to the server, check connection')
        time.sleep(10)

def message(client, feed_id, payload):
    """Callback function that responds to messages received from subscribed
    feeds"""

    logger.debug('Feed {0} received new value:\t{1}'.format(feed_id, payload))

    if feed_id == 'alarm-set':
        # If new alarm status is different, update
        if payload != alarm['set']:
            alarm['set'] = payload
    elif feed_id == 'alarm-time':
        # If new alarm time is different from saved time, update
        if payload != alarm['alarmTimeShort']:
            try:
                alarm['alarmTimeShort'] = payload
                setTime = payload.split(':',1)
                now = datetime.now()
                if (now.hour >= int(setTime[0]) and now.minute >= int(setTime[1])):
                    delta = timedelta(days=1)
                    now += delta
                alarm['alarmTimeLong'] = now.replace(hour=int(setTime[0]), minute=int(setTime[1]), second=0, microsecond=0)
                logger.info('Alarm set:\t{0}'.format(alarm['alarmTimeLong'].strftime('%Y-%m-%d %H:%M:%S')))
            except:
                logger.info('Bad alarm time given')
    elif feed_id == 'alarm-server-ping':
        # Respond to ping
        if payload == 'ping':
            aio_client.publish('alarm-server-ping', 'pong')
            playPong()
            logger.info('Ponged')
    elif feed_id == 'alarm-snooze-poke':
        # Respond to poke from snooze button by resetting and printing debug messages
        if payload == 'ON':
            aio_client.publish('alarm-snooze-poke', 'OFF')
            logger.info('Snooze pressed')
            logger.debug('Now:\t{0}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            logger.debug('Alarm:\t{0}'.format(alarm['alarmTimeLong'].strftime('%Y-%m-%d %H:%M:%S')))

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    # Send Quote of Day if given argument
    send_qod = False
    if len(sys.argv) > 1:
        if sys.argv[1] == '-q' or sys.argv[1] == '--qod':
            send_qod = True

    alarm = {
        'set': 'OFF',
        'ringing': 'OFF',
        'alarmTimeShort': '00:00',
        'alarmTimeLong': datetime.now(),
        'alarmTimeLast': datetime.now()
    }

    # Adafruit IO credentials and setup
    ADAFRUIT_IO_KEY      = 'api_key'
    ADAFRUIT_IO_USERNAME = 'username'
    aio_client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

    aio_client.on_connect       = connected
    aio_client.on_disconnect    = disconnected
    aio_client.on_message       = message

    aio_client.connect()
    aio_client.loop_background()

    # Pygame mixer
    mixer.init()

    if send_qod:
        # Twilio credentials and setup
        TWILIO_ACCOUNT_SID = 'sid'
        TWILIO_AUTH_TOKEN = 'token'

        twilio_client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        TWILIO_NUMBER = '+15555555555'
        MY_NUMBER = '+15558675309'

    lastHeartbeat = datetime.now()
    while True:
        now = datetime.now()
        # Every minute, send heartbeat to keep connection alive (possibly unecessary, need to determine error)
        if now >= lastHeartbeat + timedelta(seconds=60):
            logging.debug('Heartbeat pong')
            try:
                aio_client.publish('alarm-server-ping', 'pong')
            except errors.RequestError as e:
                logger.error(e)
            lastHeartbeat = now
        if alarm['set'] == 'ON':
            # add error catching for if publishing fails
            if now >= alarm['alarmTimeLong'] and alarm['ringing'] == 'OFF' and alarm['alarmTimeLong'] != alarm['alarmTimeLast']:
                playAlarm()
                alarm['ringing'] = 'ON'
                try:
                    aio_client.publish('alarm-ringing', alarm['ringing'])
                except errors.RequestError as e:
                    logger.error(e)
                alarm['alarmTimeLast'] = alarm['alarmTimeLong']
                logger.info('Ringing')
        else:
            if alarm['ringing'] == 'ON':
                stopAlarm()
                alarm['ringing'] = 'OFF'
                try:
                    aio_client.publish('alarm-ringing', alarm['ringing'])
                except errors.RequestError as e:
                    logger.error(e)
                if send_qod: getQOD()
                logger.info('Snoozed')
        time.sleep(1)
