# OctoPrint-LightControls

This plugin allows the user to easilly configure and control a PWM light for Raspberry PI GPIOs. 
The Light controls will show up on the controls tab as shown in the screenshots below.
Additionally, the user can configure light values per light control entity for various Octoprint events such as printer connect / disconnect, print start / end, ...

## Screenshots

![LightControls_ControlPanel](extras/screenshots/LightControls_ControlPanel.png)
![LightControls_Settings](extras/screenshots/LightControls_Settings.png)

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/RoboMagus/OctoPrint-LightControls/archive/main.zip

## Configuration

Many PWM controlled Lights can be added through the plugins settings menu.
In the top section you can add the light and give it a name, select the pin to use, etc.
Enabling and Disabling the lights automatically on e.g. print start / stop can be configured in the section below. Here you can enter the light value as a percentage of full brightness. Empty fields imply the light will remain untouched when the event occurs.
