# NHA_AlarmClock_Server

An alarm clock server designed to interface with Adafruit IO through MQTT and be used with an ESP8266-based wireless snooze button. Alarm is set via feeds from Adafruit IO and can be managed through a custom dashboard on their site or through other MQTT apps. Also can pull a quote of the day from quotesondesign.com and send it through SMS via Twilio (external setup needed). Part of the Nolando Home Automation (NHA) system.

## Usage

Run with Python from command line or terminal, adding `-q` to optionally enable quote of the day feature:

```
python NHA_AlarmClock_Server.py
```

## Requirements

Python 2.7 and pip packages `adafruit-io`, `pygame` and `twilio`.
