# coding=utf-8
from __future__ import absolute_import

import copy
import octoprint.plugin
from octoprint.events import eventManager, Events
from rpi_hardware_pwm import HardwarePWM
import sys, traceback
import RPi.GPIO as GPIO
import flask

def clamp(n, _min, _max):
    return max(_min, min(n, _max))

# Wrap 'HardwarePWM' added function ChangeDutyCycle to internal 'change_duty_cycle'
def ChangeDutyCycleWrapper(self, val):
    self.change_duty_cycle(val)

HardwarePWM.ChangeDutyCycle = ChangeDutyCycleWrapper

class LightcontrolsPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            octoprint.plugin.SimpleApiPlugin,
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.ShutdownPlugin ):

    defaultEntry = {'name': '',
                    'pin': '',
                    'ispwm': True,
                    'frequency': 250,
                    'inverted': False,
                    'onOctoprintStartValue': '',
                    'onConnectValue': '',
                    'onDisconnectValue': '',
                    'onPrintStartValue': '',
                    'onPrintPausedValue': '',
                    'onPrintResumedValue': '',
                    'onPrintEndValue': '' }

    def __init__(self):
        self.Lights = {}
        # conversion tables from board pins to BCM
        self._pin_to_gpio_rev1 = [-1, -1, -1, 0, -1, 1, -1, 4, 14, -1, 15, 17, 18, 21, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev2 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev3 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, 5, -1, 6, 12, 13, -1, 19, 16, 26, 20, -1, 21 ]

        self._gpio_to_pin_rev1 = self._create_gpio_to_pin_array(self._pin_to_gpio_rev1)
        self._gpio_to_pin_rev2 = self._create_gpio_to_pin_array(self._pin_to_gpio_rev2)
        self._gpio_to_pin_rev3 = self._create_gpio_to_pin_array(self._pin_to_gpio_rev3)

    def _create_gpio_to_pin_array(self, array):
        inv = [-1]*30
        for idx, value in enumerate(array):
            if value > -1:
                inv[value] = idx
        return inv

    def _gpio_board_to_bcm(self, pin):
        if GPIO.RPI_REVISION == 1:
            pin_to_gpio = self._pin_to_gpio_rev1
        elif GPIO.RPI_REVISION == 2:
            pin_to_gpio = self._pin_to_gpio_rev2
        else:
            pin_to_gpio = self._pin_to_gpio_rev3

        return pin_to_gpio[pin]

    def _gpio_bcm_to_board(self, pin):
        if GPIO.RPI_REVISION == 1:
            gpio_to_pin = self._gpio_to_pin_rev1
        elif GPIO.RPI_REVISION == 2:
            gpio_to_pin = self._gpio_to_pin_rev2
        else:
            gpio_to_pin = self._gpio_to_pin_rev3

        return gpio_to_pin[pin]

    def _gpio_get_pin(self, pin):
        if GPIO.getmode() == GPIO.BOARD:
            return self._gpio_bcm_to_board(pin)
        elif GPIO.getmode() == GPIO.BCM:
            return pin
        else:
            return 0

    def _get_hw_pwm_channel(self, pin):
        if pin in [12, 18]:
            return 0
        elif pin in [13, 19]:
            return 1
        else:
            return None
    
    def _is_hw_pwm_pin(self, pin):
        return pin in [12, 13, 18, 19]

    def _get_gpio_mode_string(self):
        if GPIO.getmode() == GPIO.BOARD:
            return "BOARD"
        elif GPIO.getmode() == GPIO.BCM:
            return "BCM"
        else:
            return "?"

    def configure_gpio(self):
        self._logger.debug("Running RPi.GPIO version %s" % GPIO.VERSION)
        if GPIO.VERSION < "0.6":
            self._logger.error("RPi.GPIO version 0.6.0 or greater required.")

        GPIO.setwarnings(False)

        if GPIO.getmode() is None:
            GPIO.setmode(GPIO.BCM)

    def gpio_startup(self, pin, settings):
        self._logger.debug("LightControls gpio_startup, pin: {}, settings: {}".format(pin, settings))
        if pin and pin >= 0:
            # Remove to re-add if already present:
            if pin in self.Lights:
                self.gpio_cleanup(pin)

            try:
                self.Lights[pin] = copy.deepcopy(settings)
                if settings["ispwm"]:
                    if self._is_hw_pwm_pin(self._gpio_get_pin(pin)):
                        try:
                            self.Lights[pin]["pwm"] = HardwarePWM(self._get_hw_pwm_channel(self._gpio_get_pin(pin)), int(settings["frequency"]))
                            self._logger.debug("Setup hardware PWM succeded!")
                        except Exception as e:
                            self._logger.error("Tried to setup pin {} as hardware PWM on channel {}, but failed:".format(pin, self._get_hw_pwm_channel(self._gpio_get_pin(pin))))
                            self._logger.error(e)
                            self._logger.warning("Setting up as software PWM instead...")
                            self._logger.warning("If your LEDs appear to be flickering, look into hardware PWM.")
                            GPIO.setup(self._gpio_get_pin(pin), GPIO.OUT)
                            self.Lights[pin]["pwm"] = GPIO.PWM(self._gpio_get_pin(pin), int(settings["frequency"]))
                    else:
                        GPIO.setup(self._gpio_get_pin(pin), GPIO.OUT)
                        self.Lights[pin]["pwm"] = GPIO.PWM(self._gpio_get_pin(pin), int(settings["frequency"]))
                    self.Lights[pin]["pwm"].start(100 if self.Lights[pin]["inverted"] else 0)
                else:
                    GPIO.setup(self._gpio_get_pin(pin), GPIO.OUT)
                    GPIO.output(self._gpio_get_pin(pin), 1 if self.Lights[pin]["inverted"] else 0)

                self.Lights[pin]["value"] = 0
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self._logger.error("exception in gpio_startup(): {}".format(exc_type))
                self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))

        else:
            self._logger.warning(f"Configured pin ({pin}) not an integer")

    def gpio_cleanup(self, pin):
        self._logger.debug("LightControls gpio_cleanup, pin: {}".format(pin))
        if pin in self.Lights:
            try:
                if self.Lights[pin]["ispwm"]:
                    self.Lights[pin]["pwm"].stop()
                del self.Lights[pin]
                GPIO.cleanup(self._gpio_get_pin(pin))
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self._logger.error("exception in gpio_cleanup(): {}".format(exc_type))
                self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))


    def gpio_set_value(self, pin, value):
        if pin in self.Lights:
            if self.Lights[pin]["ispwm"]:
                iVal = int(value)
                val = ((100 - iVal) if self.Lights[pin]["inverted"] else iVal)
                self._logger.debug("LightControls pin({}).setValue({}), inverted: {}".format(pin, iVal, self.Lights[pin]["inverted"]))
                self.Lights[pin]["pwm"].ChangeDutyCycle(val)
                if iVal != self.Lights[pin]["value"]:
                    self._plugin_manager.send_plugin_message(self._identifier, dict(pin=pin, value=iVal))
                self.Lights[pin]["value"] = iVal
            else:
                iVal = min(int(value), 1)
                val = ((1-iVal) if self.Lights[pin]["inverted"] else iVal)
                # Value for non PWM pins is either 0 (off) or 100 (on), for consistency on the interfaces...
                iVal = iVal*100
                self._logger.debug("LightControls pin({}).setValue({}), inverted: {}".format(pin, iVal, self.Lights[pin]["inverted"]))
                GPIO.output(self._gpio_get_pin(pin), val)
                if iVal != self.Lights[pin]["value"]:
                    self._plugin_manager.send_plugin_message(self._identifier, dict(pin=pin, value=iVal))
                self.Lights[pin]["value"] = iVal

    def gpio_get_value(self, pin):
        if pin in self.Lights:
            return self.Lights[pin]["value"]
        return None

    def send_light_values(self):
        self._logger.debug("SendingLightValues")
        for pin in self.Lights:
            self._plugin_manager.send_plugin_message(self._identifier, dict(pin=pin, value=self.Lights[pin]["value"]))

    def LightName2PinNumber(self, name):
        pinNumber = [pin for pin, light in self.Lights.items() if light['name'] == name]
        self._logger.debug("LightName2PinNumber() name: '{}', pin: {}".format(name, pinNumber))
        if not pinNumber:
            return None
        else:
            return pinNumber[0]

    ##~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return dict(
            setLightValue=["pin", "percentage"],
            getLightValues=[],
        )

    def on_api_command(self, command, data):
        if command == "setLightValue":
            try:
                pin = data["pin"]
                value = data["percentage"]
                self.gpio_set_value(pin, value)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self._logger.error("exception in setLightValue(): {}".format(exc_type))
                self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))
        elif command == "getLightValues":
            self.send_light_values()

    def on_api_get(self, request):
        self._logger.debug("on_api_get({}).Json: ".format(request, request.get_json()))
        if request == "getLightValues":
            response = dict()
            for pin in self.Lights:
                response(pin=self.Lights[pin]["value"])
            return flask.jsonify(response)

    def is_api_adminonly(self):
        return True

    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        if event == Events.CONNECTED:
            # Client connected. Send current UI settings:
            for pin in self.Lights:
                if self.Lights[pin]['onConnectValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onConnectValue'])
        elif event == Events.DISCONNECTED:
            for pin in self.Lights:
                if self.Lights[pin]['onDisconnectValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onDisconnectValue'])
        elif event == Events.PRINT_STARTED:
            for pin in self.Lights:
                if self.Lights[pin]['onPrintStartValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintStartValue'])
        elif event == Events.PRINT_PAUSED:
            for pin in self.Lights:
                if self.Lights[pin]['onPrintPausedValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintPausedValue'])
        elif event == Events.PRINT_RESUMED:
            for pin in self.Lights:
                if self.Lights[pin]['onPrintResumedValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintResumedValue'])
        elif event == Events.PRINT_DONE or event == Events.PRINT_CANCELLED or event == Events.PRINT_FAILED:
            for pin in self.Lights:
                if self.Lights[pin]['onPrintEndValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintEndValue'])

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict (
            light_controls=[{
                'name': '',
                'pin': None,
                'ispwm': True,
                'frequency': 250,
                'inverted': False,
                'onOctoprintStartValue': '',
                'onConnectValue': '',
                'onDisconnectValue': '',
                'onPrintStartValue': '',
                'onPrintPausedValue': '',
                'onPrintResumedValue': '',
                'onPrintEndValue': ''
            }]
        )

    def checkLightControlEntryKeys(self, entry):
        return set(self.defaultEntry.keys()) == set(entry.keys())

    def updateLightControlEntry(self, entry):
        _entry = copy.deepcopy(self.defaultEntry)
        for key in entry:
            _entry[key]=entry[key]
        self._logger.info("Updated LightControlEntry from: {}, to {}".format(entry, _entry))
        return _entry

    def on_settings_initialized(self):
        lightControls_in = self._settings.get(["light_controls"])
        self._logger.debug("LightControls settings initialized: '{}'".format(lightControls_in))

        # Ensure GPIO is initialized
        self.configure_gpio()

        # Remove entries when their pin is undefined to avoid errors later on.
        lightControls = [ctrl for ctrl in lightControls_in if (ctrl['pin'] or -1) >= 0]

        # On initialization check for incomplete settings!
        modified=False
        for idx, ctrl in enumerate(lightControls):
            if not self.checkLightControlEntryKeys(ctrl):
                lightControls[idx] = self.updateLightControlEntry(ctrl)
                modified=True

            self.gpio_startup(lightControls[idx]["pin"], lightControls[idx])

        if modified:
            self._settings.set(["light_controls"], lightControls)

        self._logger.debug("LightControls pruned settings after initialize: '{}'".format(lightControls))

    def on_settings_save(self, data):
        # Get old settings:

        # Get updated settings
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        # Ensure GPIO is initialized
        self.configure_gpio()

        # Cleanup old Gpio handles for lights that may be removed
        for pin in list(self.Lights.keys()):
            self.gpio_cleanup(pin)

        # Handle changes (if new != old)
        self._logger.debug("LightControls settings saved: '{}'".format(self._settings.get(["light_controls"])))
        for controls in self._settings.get(["light_controls"]):
            self.gpio_startup(controls["pin"], controls)


    ##~~ StartupPlugin mixin

    def on_after_startup(self):
        # Ensure GPIO is initialized
        self.configure_gpio()

        # start gpio
        for controls in self._settings.get(["light_controls"]):
            self.gpio_startup(controls["pin"], controls)

        # Set all default Octoprint Startup values if available:
        for pin in self.Lights:
            if self.Lights[pin]['onOctoprintStartValue']:
                self.gpio_set_value(pin, self.Lights[pin]['onOctoprintStartValue'])


    ##~~ ShutdownPlugin mixin

    def on_shutdown(self):
        for pin in list(self.Lights.keys()):
            self.gpio_cleanup(pin)
        GPIO.cleanup()
        self._logger.debug("LightControls shutdown")


    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/LightControls.js"],
        }


    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="settings", template="lightcontrols_settings.jinja2", custom_bindings=True),
            dict(type="generic", template="lightcontrols.jinja2", custom_bindings=True)
        ]


    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "LightControls": {
                "displayName": "Lightcontrols Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "RoboMagus",
                "repo": "OctoPrint-LightControls",
                "current": self._plugin_version,

                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "comittish": ["main"],
                },
                "prerelease_branches": [
                    {
                        "name": "Release Candidate",
                        "branch": "RC",
                        "comittish": ["RC", "main"],
                    },
                    {
                        "name": "Development",
                        "branch": "dev",
                        "comittish": ["dev", "RC", "main"],
                    }
                ],

                # update method: pip
                "pip": "https://github.com/RoboMagus/OctoPrint-LightControls/archive/{target_version}.zip",
            }
        }

    
    ##~~ Atcommand hook

    def atcommand_handler(self, _comm, _phase, command, parameters, tags=None, *args, **kwargs):
        if command != "LIGHTCONTROL":
            return

        [light, value, *_] = parameters.split() + ["", ""]
        self._logger.debug(f"@Command. Light: '{light}', Value: {value}")
        
        if light and value:
            pinNumber = self.LightName2PinNumber(light)
            self.gpio_set_value(pinNumber, clamp(int(value), 0, 100))
        else:
            self._logger.warning("@Command incomplete! Needs format '@LIGHTCONTROL [LightName] [LightValue]'")

        return None # No further actions required

        
    ##~~ Helper functions

    def ext_get_light_names(self):
        """
        Get light names
        :return: array of light names
        """
        val = [light['name'] for (pin, light) in self.Lights.items()]
        self._logger.info("EXT. get_light_names(): {}".format(val))
        return val

    def ext_get_light_value(self, light_name=None):
        """
        Get light value from provided light name
        :param light_name: Name of the light
        :return: value from 0 to 100
        """
        pinNumber = self.LightName2PinNumber(light_name)
        val = self.gpio_get_value(pinNumber)
        self._logger.info("EXT. get_light_value(light_name: '{}'): {}".format(light_name, val))
        return val

    def ext_set_light_value(self, light_name=None, light_value=0):
        """
        Sets light value for provided light name
        :param light_name: Name of the light
        :param light_value: value for the light (0 to 100)
        :return: set value if successful, None otherwise.
        """
        self._logger.info(f"EXT. set_light_value(light_name: '{light_name}', light_value: {light_value})")
        if light_name and light_value != None:
            pinNumber = self.LightName2PinNumber(light_name)
            self.gpio_set_value(pinNumber, clamp(light_value, 0, 100))
            return self.gpio_get_value(pinNumber)

        return None


__plugin_name__ = "LightControls"
__plugin_pythoncompat__ = ">=3,<4" # only python 3

def __plugin_load__():
    plugin = LightcontrolsPlugin()

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        get_light_names=plugin.ext_get_light_names,
        get_light_value=plugin.ext_get_light_value,
        set_light_value=plugin.ext_set_light_value
    )

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.atcommand.sending": __plugin_implementation__.atcommand_handler
    }
