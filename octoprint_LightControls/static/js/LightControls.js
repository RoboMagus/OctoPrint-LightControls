/*
 * View model for OctoPrint-LightControls
 *
 * Author: RoboMagus
 * License: AGPLv3
 */
$(function() {
    function LightcontrolsViewModel(parameters) {
        var self = this;

        var PLUGIN_ID = "LightControls"

        self.settings = parameters[0];
        self.control = parameters[1];

        self.gpio_pin_options = [4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27];
        self.light_controls = ko.observableArray(); // Raw settings
        self.lights = ko.observableArray(); // light states

        ko.subscribable.fn.withUpdater = function (handler, target, identifier) {
            var self = this;   
        
            var _oldValue;
            this.subscribe(function (oldValue) {
                _oldValue = oldValue;
            }, null, 'beforeChange');

            this.subscribe(function (newValue) {
                handler.call(target, _oldValue, newValue, identifier);
            });
            this.extend({ rateLimit: 100 });
        
            return this;     
        };

        var sliderUpdate = function (oldvalue, newvalue, identifier) {
            if( oldvalue != newvalue) {            
                // communicate update to backend
                $.ajax({
                    url: API_BASEURL + "plugin/"+PLUGIN_ID,
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "setLightValue",
                        pin: identifier,
                        percentage: newvalue
                    }),
                    contentType: "application/json; charset=UTF-8"
                }).done(function(data){

                }).always(function(){

                });
            }
        }

        self.requestDistributeLightValues = function() {
            // console.log("Requesting light levels!");
            $.ajax({
                url: API_BASEURL + "plugin/"+PLUGIN_ID,
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "getLightValues",
                }),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data){

            }).always(function(){

            });
        }

        self.updateLightsStructure = function() {
            self.lights([]);
            ko.utils.arrayForEach(self.settings.settings.plugins.LightControls.light_controls(), function (item, index) {
                self.lights.push({ 
                    name: item.name, 
                    pin: item.pin,
                    light_val: ko.observable(0).withUpdater(sliderUpdate, self, item.pin()) });
            });
            // Request values whenever the light structure is updated!
            self.requestDistributeLightValues();
        };

        self.onBeforeBinding = function() {
            // self.updateLightsStructure();
        };

        self.onAfterBinding = function() {
            // I want this to be placed after MultiWebcam :)
            var lightsControl = $('#lightcontrols');
            var containerGeneral = $('#control-jog-general');

            lightsControl.insertAfter(containerGeneral);
            lightsControl.css('display', '');

            self.updateLightsStructure();
        };

        self.onSettingsBeforeSave = function() {
            // ko.utils.arrayForEach(self.settings.settings.plugins.LightControls.light_controls(), function (item, index) {
            // });
        };

        self.onEventSettingsUpdated = function(payload) {
			self.settings.requestData();
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
            self.updateLightsStructure();
        };

        self.addLightControl = function() {
            self.settings.settings.plugins.LightControls.light_controls.push({
                name: ko.observable('Light '+self.light_controls().length), 
                pin: ko.observable(''),
                ispwm: ko.observable('true'),
                frequency: ko.observable('250'),
                inverted: ko.observable('false'), 
                onOctoprintStartValue: ko.observable(''),
                onConnectValue: ko.observable(''),
                onDisconnectValue: ko.observable(''),
                onPrintStartValue: ko.observable(''),
                onPrintPausedValue: ko.observable(''),
                onPrintResumedValue: ko.observable(''),
                onPrintEndValue: ko.observable('') });
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
        };

        self.removeLightControl = function(profile) {
            self.settings.settings.plugins.LightControls.light_controls.remove(profile);
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == PLUGIN_ID) {
                if (data.pin != undefined && data.value != undefined) {        
                    ko.utils.arrayForEach(self.lights(), function(item) {
                        if(item.pin() == data.pin) {
                            item.light_val(data.value);
                        }
                    });
                }
            }
        }
    }


    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: LightcontrolsViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel", "controlViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_LightControls, #tab_plugin_LightControls, ...
        elements: [ "#settings_plugin_lightcontrols_form", "#lightcontrols" ]
    });
});
