import requests
import hmac
import time
import os.path

# Disable warning due to SubjectAltNameWarning in certificate
requests.packages.urllib3.disable_warnings()

SUPPORTED_SERVICES = ['basic-1', 'minimal-2', 'basic-2']


class UnsupportedDevice(Exception):
    pass


class Robot:
    """Data and methods for interacting with a Neato Botvac Connected vacuum robot"""

    def __init__(self, serial, secret, traits, name=''):
        """
        Initialize robot

        :param serial: Robot serial
        :param secret: Robot secret
        :param name: Name of robot (optional)
        :param traits: Extras the robot supports
        """
        self.name = name
        self.serial = serial
        self.secret = secret
        self.traits = traits

        self._url = 'https://nucleo.neatocloud.com/vendors/neato/robots/{}/messages'.format(self.serial)
        self._headers = {'Accept': 'application/vnd.neato.nucleo.v1'}

        if self.service_version not in SUPPORTED_SERVICES:
            raise UnsupportedDevice("Version " + self.service_version + " of service houseCleaning is not known")

    def __str__(self):
        return "Name: %s, Serial: %s, Secret: %s Traits: %s" % (self.name, self.serial, self.secret, self.traits)

    def _message(self, json):
        """
        Sends message to robot with data from parameter 'json'
        :param json: dict containing data to send
        :return: server response
        """

        cert_path = os.path.join(os.path.dirname(__file__), 'cert', 'neatocloud.com.crt')
        response = requests.post(self._url,
                                 json=json,
                                 verify=cert_path,
                                 auth=Auth(self.serial, self.secret),
                                 headers=self._headers)
        response.raise_for_status()
        return response

    def start_cleaning(self, mode=2, navigation_mode=2):
        # mode & naivigation_mode used if applicable to service version
        # mode: 1 eco, 2 turbo
        # navigation_mode: 1 normal, 2 extra care
        
        if self.service_version == 'basic-1':
            json = {'reqId': "1",
                    'cmd': "startCleaning",
                    'params': {
                        'category': 2,
                        'mode': mode,
                        'modifier': 1}
                    }
        elif self.service_version == 'minimal-2':
            json = {'reqId': "1",
                    'cmd': "startCleaning",
                    'params': {
                        'category': 2,
                        "navigationMode": navigation_mode}
                    }
        else:   # self.service_version == 'basic-2'
            json = {'reqId': "1",
                    'cmd': "startCleaning",
                    'params': {
                        'category': 2,
                        'mode': mode,
                        'modifier': 1,
                        "navigationMode": navigation_mode}
                    }
        
        return self._message(json)

    def pause_cleaning(self):
        return self._message({'reqId': "1", 'cmd': "pauseCleaning"})

    def resume_cleaning(self):
        return self._message({'reqId': "1", 'cmd': "resumeCleaning"})

    def stop_cleaning(self):
        return self._message({'reqId': "1", 'cmd': "stopCleaning"})

    def send_to_base(self):
        return self._message({'reqId': "1", 'cmd': "sendToBase"})

    def get_robot_state(self):
        return self._message({'reqId': "1", 'cmd': "getRobotState"})

    def enable_schedule(self):
        return self._message({'reqId': "1", 'cmd': "enableSchedule"})

    def disable_schedule(self):
        return self._message({'reqId': "1", 'cmd': "disableSchedule"})

    def get_schedule(self):
        return self._message({'reqId': "1", 'cmd': "getSchedule"})

    @property
    def schedule_enabled(self):
        return self.get_robot_state().json()['details']['isScheduleEnabled']

    @schedule_enabled.setter
    def schedule_enabled(self, enable):
        if enable:
            self.enable_schedule()
        else:
            self.disable_schedule()

    @property
    def state(self):
        return self.get_robot_state().json()

    @property
    def available_services(self):
        return self.state['availableServices']

    @property
    def service_version(self):
        return self.available_services['houseCleaning']


class Auth(requests.auth.AuthBase):
    """Create headers for request authentication"""

    def __init__(self, serial, secret):
        self.serial = serial
        self.secret = secret

    def __call__(self, request):
        date = time.strftime('%a, %d %h %Y %H:%M:%S', time.gmtime()) + ' GMT'

        signing = hmac.new(key=self.secret.encode('utf8'),
                           msg='\n'.join([self.serial.lower(), date, request.body.decode('utf8')]).encode('utf8'),
                           digestmod='sha256')

        request.headers['Date'] = date
        request.headers['Authorization'] = "NEATOAPP " + signing.hexdigest()

        return request
