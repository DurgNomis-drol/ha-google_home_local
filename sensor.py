"""Platform for sensor integration."""
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.const import STATE_ON, STATE_OFF, HTTP_OK, CONF_USERNAME
from homeassistant.components.sensor import PLATFORM_SCHEMA
import voluptuous as vol
import json
import requests
import logging

from .glocaltokens.client import GLocalAuthenticationTokens
from datetime import datetime, timedelta
import urllib3
#urllib3.disable_warnings()

_LOGGER = logging.getLogger(__name__)

CONF_PASSWORD = 'app_password'
CONF_DEVICE_IP = 'device_ip'
CONF_DEVICE_NAME = 'device_name'
CONF_MASTER_TOKEN = 'master_token'

DEFAULT_MASTER_TOKEN = None

SCAN_INTERVAL = timedelta(seconds=15)

# GET Request Timeout
TIMEOUT = 10

ENDPOINT = '/assistant/alarms'

DOMAIN = "google_home_local"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_MASTER_TOKEN): cv.string,
        vol.Required(CONF_DEVICE_IP): cv.string,
        vol.Required(CONF_DEVICE_NAME): cv.string,
    }
)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor platform."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    if config.get(CONF_MASTER_TOKEN):
        master_token = config.get(CONF_MASTER_TOKEN)
    else:
        master_token = DEFAULT_MASTER_TOKEN
    device_ip = config.get(CONF_DEVICE_IP)
    device_name = config.get(CONF_DEVICE_NAME)

    data = ghlocalAPI(username, password, device_ip, device_name, master_token)
    data.update()

    add_devices(
        [Timer_sensor(device_name, data),
        Alarm_sensor(device_name, data)],
        True
    )

    def delete(call):
        """Delete service."""
        id = call.data.get('id')
        _LOGGER.info('Received data', call.data)
        data.delete(id)

    # Register our service with Home Assistant.
    hass.services.register(DOMAIN, 'delete', delete)


class Timer_sensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, data):
        """Initialize the sensor."""
        self._name = name + " timers"
        self.data = data
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'timers': self.data.timers,
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:timer-sand"

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """

        self.data.update()

        if len(self.data.timers) > 0:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF

class Alarm_sensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, data):
        """Initialize the sensor."""
        self._name = name + " alarms"
        self.data = data
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'alarms': self.data.alarms,
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:alarm-multiple"

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """

        self.data.update()

        if len(self.data.alarms) > 0:
            self._state = self.data.alarms[0]['date_time']
        else:
            self._state = STATE_OFF

class ghlocalAPI():

    def __init__(self, username, password, device_ip, device_name, master_token=None):
        self.timers = []
        self.alarms = []
        self.username = username
        self.password = password
        self.master_token = master_token
        self.device_ip = device_ip
        self.device_name = device_name

        self.client = GLocalAuthenticationTokens(
          username=self.username,
          password=self.password,
          master_token=self.master_token
        )

    def delete(self, id):

        google_devices = self.client.get_google_devices_json()

        local_token = next(item['localAuthToken'] for item in google_devices if item["deviceName"] == self.device_name)
        #local_token = google_devices[1]['localAuthToken']

        url = 'https://' + self.device_ip + ':8443/setup' + ENDPOINT + '/delete'
        header = {'cast-local-authorization-token': local_token,
                  'content-type': 'application/json'}
        data = {"ids": [id]}

        response = requests.post(url, data=json.dumps(data), headers=header, verify=False, timeout=TIMEOUT)

        if response.status_code != HTTP_OK:
            _LOGGER.error("API returned {}".format(response.status_code))
            return

        result = response.json()

        if result['success'] != True:
            _LOGGER.error("API returned success false")
            return

    def update(self):

        google_devices = self.client.get_google_devices_json()

        local_token = next(item['localAuthToken'] for item in google_devices if item["deviceName"] == self.device_name)
        #local_token = google_devices[1]['localAuthToken']

        url = 'https://' + self.device_ip + ':8443/setup' + ENDPOINT
        header = {'cast-local-authorization-token': local_token,
                  'content-type': 'application/json'}

        response = requests.get(url, headers=header, verify=False, timeout=TIMEOUT)

        if response.status_code != HTTP_OK:
            _LOGGER.error("API returned {}".format(response.status_code))
            return

        result = response.json()

        if "timer" not in result or "alarm" not in result:
            _LOGGER.error("API returned unknown json structure")
            return

        self.timers = []
        self.alarms = []

        for x in range(len(result['timer'])):

            self.timers = result['timer']

            timestamp_ms = result['timer'][x]['fire_time']
            timestamp = timestamp_ms / 1000
            humantime = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            self.timers[x]['date_time'] = humantime

            duration_ms = result['timer'][x]['original_duration']
            duration = duration_ms / 1000
            humanduration = datetime.utcfromtimestamp(duration).strftime('%H:%M:%S')
            self.timers[x]['duration'] = humanduration

        for x in range(len(result['alarm'])):

            self.alarms = result['alarm']

            timestamp_ms = result['alarm'][x]['fire_time']
            timestamp = timestamp_ms / 1000
            humantime = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%S.%fZ%Z')
            localtime = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self.alarms[x]['date_time'] = humantime
            self.alarms[x]['local_time'] = localtime
