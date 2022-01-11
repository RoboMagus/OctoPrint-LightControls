# coding=utf-8
from __future__ import absolute_import

import copy
import octoprint.plugin
from octoprint.events import eventManager, Events
import sys, traceback
import RPi.GPIO as GPIO
import flask

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
                
            GPIO.setup(self._gpio_get_pin(pin), GPIO.OUT)
            try:
                self.Lights[pin] = copy.deepcopy(settings)
                if settings["ispwm"]:
                    self.Lights[pin]['pwm'] = GPIO.PWM(self._gpio_get_pin(pin), int(settings["frequency"]))
                    self.Lights[pin]['pwm'].start(100 if self.Lights[pin]["inverted"] else 0)
                else:
                    GPIO.output(self._gpio_get_pin(pin), 1 if self.Lights[pin]["inverted"] else 0) 

                self.Lights[pin]['value'] = 0
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


    def send_light_values(self):
        self._logger.debug("SendingLightValues")
        for pin in self.Lights:
            self._plugin_manager.send_plugin_message(self._identifier, dict(pin=pin, value=self.Lights[pin]["value"]))

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
        # Client connected, send current ui setting:
        if event == Events.CONNECTED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
                if self.Lights[pin]['onConnectValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onConnectValue'])
        elif event == Events.DISCONNECTED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
                if self.Lights[pin]['onDisconnectValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onDisconnectValue'])
        elif event == Events.PRINT_STARTED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
                if self.Lights[pin]['onPrintStartValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintStartValue'])
        elif event == Events.PRINT_PAUSED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
                if self.Lights[pin]['onPrintPausedValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintPausedValue'])
        elif event == Events.PRINT_RESUMED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
                if self.Lights[pin]['onPrintResumedValue']:
                    self.gpio_set_value(pin, self.Lights[pin]['onPrintResumedValue'])
        elif event == Events.PRINT_DONE or event == Events.PRINT_CANCELLED or event == Events.PRINT_FAILED:
            for pin in self.Lights:
                self._logger.debug(self.Lights[pin])
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
        self._logger.info("LightControls settings initialized: '{}'".format(lightControls_in))
        
        # Ensure GPIO is initialized
        self.configure_gpio()

        # Remove entries when their pin is undefined to avoid errors later on.
        lightControls = {k: v for k,v in lightControls_in.items() if (v['pin'] or -1) >= 0}

        # On initialization check for incomplete settings!
        modified=False
        for idx, ctrl in enumerate(lightControls):
            if not self.checkLightControlEntryKeys(ctrl):
                lightControls[idx] = self.updateLightControlEntry(ctrl)
                modified=True                
                
            self.gpio_startup(lightControls[idx]["pin"], lightControls[idx])

        if modified:
            self._settings.set(["light_controls"], lightControls_pruned)

    def on_settings_save(self, data):
        # Get old settings:

        # Get updated settings
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        # Ensure GPIO is initialized
        self.configure_gpio()

        # Handle changes (if new != old)
        self._logger.info("LightControls settings saved: '{}'".format(self._settings.get(["light_controls"])))
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

                # update method: pip
                "pip": "https://github.com/RoboMagus/OctoPrint-LightControls/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "LightControls"
__plugin_pythoncompat__ = ">=3,<4" # only python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = LightcontrolsPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
