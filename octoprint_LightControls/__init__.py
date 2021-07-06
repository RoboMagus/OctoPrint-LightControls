# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import sys, traceback
import RPi.GPIO as GPIO
import flask

class LightcontrolsPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.SimpleApiPlugin,
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.ShutdownPlugin ):

    # ToDo:
    # - Add invert setting
    def __init__(self):
        self.Lights = {}

    def gpio_startup(self, pin, frequency = 200, invert = False):
        self._logger.info("LightControls gpio_startup, pin: {}, freq: {}, invert: {}".format(pin, frequency, invert))
        if pin > 0:
            if pin in self.Lights:
                self._logger.warning("Not creating PWM for pin {}. Already exists!".format(pin))
            else:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin, GPIO.OUT)
                try:
                    self.Lights[pin] = {
                        'pwm': GPIO.PWM(pin, frequency),
                        'pin': pin,
                        'invert': bool(invert) }
                    # self.Lights[pin].pwm = GPIO.PWM(pin, frequency)
                    # self.Lights[pin].pin = pin
                    # self.Lights[pin].invert = bool(invert)
                    self.Lights[pin]["pwm"].start(100 if self.Lights[pin]["invert"] else 0)
                except:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    self._logger.error("exception in setLightValue(): {}".format(exc_type))
                    self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))
                    
        else:
            self._logger.warning("Configured pin not an integer")

    def gpio_cleanup(self, pin):
        self._logger.info("LightControls gpio_cleanup, pin: {}".format(pin))
        if pin in self.Lights:
            self.Lights[pin]["pwm"].stop()
            del self.Lights[pin]

    def gpio_set_value(self, pin, value):
        if pin in self.Lights:
            val = ((int(100) - int(value)) if self.Lights[pin]["invert"] else int(value))
            self._logger.info("LightControls pin({}).setValue({}), invert: {}".format(pin, value, self.Lights[pin]["invert"]))
            self.Lights[pin]["pwm"].ChangeDutyCycle(val)

    ##~~ SimpleApiPlugin mixin
    def get_api_commands(self):
        return dict(
            setLightValue=["pin", "percentage"],
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
        # elif command == "sendGoogleAssistantBroadcast":
        #     try:
        #         message=data["message"]
        #         self.assistant_relay_broadcast(message)
        #     except:
        #         self._logger.error("Failure onsendGoogleAssistantBroadcast")


    def on_api_get(self, request):
        return flask.jsonify(foo="bar2")

    def is_api_adminonly(self):
        return True

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict (
            light_controls=[{
                'name': '',
                'pin': '',
                'ispwm': 'true',
                'frequency': 250,
                'inverted': 'false'
            }]
        )

    def on_settings_initialized(self):
        self._logger.info("LightControls settings initialized: '{}'".format(self._settings.get(["light_controls"])))
        for controls in self._settings.get(["light_controls"]):
            self.gpio_startup(controls["pin"], controls["frequency"], bool(controls["inverted"]))

    def on_settings_save(self, data):
        # Get old settings:

        # Get updated settings
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        # Handle changes (if new != old)
        self._logger.info("LightControls settings saved: '{}'".format(self._settings.get(["light_controls"])))


    ##~~ StartupPlugin mixin

    def on_after_startup(self):
        self._Lights = self._settings.get(["light_controls"])
        self._logger.info("LightControls startup: {}".format(self._Lights))
        # start gpio
        for controls in self._settings.get(["light_controls"]):
            self._logger.info("Initializing GPIO for: {}".format(controls))
            self.gpio_startup(controls["pin"], controls["frequency"], bool(controls["inverted"]))

#   def on_after_startup(self):
#       helpers = self._plugin_manager.get_helpers("mqtt", "mqtt_publish", "mqtt_subscribe", "mqtt_unsubscribe")
#       if helpers:
#           if "mqtt_subscribe" in helpers:
#               self.mqtt_subscribe = helpers["mqtt_subscribe"]
#               for relay in self._settings.get(["arrRelays"]):
#                   self._tasmota_mqtt_logger.debug(self.generate_mqtt_full_topic(relay, "stat"))
#                   self.mqtt_subscribe(self.generate_mqtt_full_topic(relay, "stat"), self._on_mqtt_subscription, kwargs=dict(top=relay["topic"],relayN=relay["relayN"]))
#           if "mqtt_publish" in helpers:
#               self.mqtt_publish = helpers["mqtt_publish"]
#               self.mqtt_publish("octoprint/plugin/tasmota", "OctoPrint-TasmotaMQTT publishing.")
#               if any(map(lambda r: r["event_on_startup"] == True, self._settings.get(["arrRelays"]))):
#                   for relay in self._settings.get(["arrRelays"]):
#                       self._tasmota_mqtt_logger.debug("powering on {} due to startup.".format(relay["topic"]))
#                       self.turn_on(relay)
#           if "mqtt_unsubscribe" in helpers:
#               self.mqtt_unsubscribe = helpers["mqtt_unsubscribe"]
#       else:
#           self._plugin_manager.send_plugin_message(self._identifier, dict(noMQTT=True))


    ##~~ ShutdownPlugin mixin

    def on_shutdown(self):
        for pin in list(self.Lights.keys()):
            self.gpio_cleanup(pin)

        self._logger.info("LightControls shutdown")

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/LightControls.js"],
            "css": ["css/LightControls.css"],
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
