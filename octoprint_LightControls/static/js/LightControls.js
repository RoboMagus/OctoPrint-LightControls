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

        self.updateLightsStructure = function() {
            ko.utils.arrayForEach(self.settings.settings.plugins.LightControls.light_controls(), function (item, index) {
                var entry = { name: item.name, 
                              pin: item.pin,
                              light_val: ko.observable(0) };
                entry.light_val.subscribe(function(value) {
                    console.log("UpdateSliderValue(%d)", value);
                });
                self.lights.push(entry);
            });
        };

        self.onBeforeBinding = function() {
            self.updateLightsStructure();
        };

        self.onAfterBinding = function() {
            // I want this to be placed after MultiWebcam :)
            var lightsControl = $('#lightcontrols');
            var containerGeneral = $('#control-jog-general');

            lightsControl.insertAfter(containerGeneral);
            lightsControl.css('display', '');
        };

        self.onSettingsBeforeSave = function() {
            // Update multicam profile for default webcam
            // ko.utils.arrayForEach(self.settings.settings.plugins.LightControls.light_controls(), function (item, index) {
            // });
        };

        self.onEventSettingsUpdated = function(payload) {
			self.settings.requestData();
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
            self.updateLightsStructure();
        };

        self.addLightControl = function() {
            console.log("Adding new light!");
            self.settings.settings.plugins.LightControls.light_controls.push({
                name: ko.observable('Light '+self.light_controls().length), 
                pin: ko.observable(''),
                ispwm: ko.observable('true'),
                frequency: ko.observable('250'),
                inverted: ko.observable('false') });
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
        };

        self.removeLightControl = function(profile) {
            self.settings.settings.plugins.LightControls.light_controls.remove(profile);
            self.light_controls(self.settings.settings.plugins.LightControls.light_controls());
        };

        self.sliderEvent = function(control, event) {
            console.log("Slider event for: ");
            console.log(control);
        };

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
