# ha-google_home_local
Custom component for homeassistant

## THIS IS STILL VERT MUCH AN ALPHA

app_password doesnt work as of right now, and i havent found an solution for this yet.

As of now this component only retieves one device per setup.

## Installation
This will only install under Arm/Raspberry Pi 4 docker if you install grpcio and grpcio-tools manually and for that you need to add "apk add gcc g++ linux-headers" first. This is because homeassistant is build on Alpine.

Create a folder named ha-google_home_local in your custom_components folder and copy these files in there (excluding readme).

```yaml
sensor:
  - platform: google_home_local
    username: "email excluding @gmail.com"
    app_password: "App password"
    master_token: "Master token retrieved from get_tokens.py"
    device_ip: "ip of your google home device"
    device_name: "Name of your google home device"
```

## get_tokens.py
You can find it here: [link](https://github.com/leikoilja/glocaltokens/tree/master/glocaltokens)

## Sensors

2 sensors wil be generated from this, one named sensor."device name"-timers and one named sensor."device name"-alarms.

## Credit
[leikoilja](https://github.com/leikoilja) for making glocaltokens python package

[rithvikvibhu](https://github.com/rithvikvibhu) for finding a way to make all this possible.
