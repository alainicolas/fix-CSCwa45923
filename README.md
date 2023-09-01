# Fix CSCwa45923

Python script to check if a Nexus device is impacted with CSCwa45923 (also known as CSCvx53634) and to
fix it if needed. 



usage: floodlist_fix.py [-h] [-s] [-f] [-l]

Default behavior : Check for issues with console outputs.

```
optional arguments:
  -h, --help    show this help message and exit
  -s, --silent  Run the script without any console output.
  -f, --fix     Run the fix if an issue is found.
  -l, --log     Log the output of each device in a text file.
```
## Setup
**Template folder :**

list_ip.yaml :  List of ip you want to check. 

testbed.tpl :   Don't forget to setup your testbed.

```                
username: nxos_username
password: nxos_password
                
vps is the linux rebound server (could be removed)
username: rebound_server_username
```

**Outputs folder :**

Will save data for broken devices.  
  
  
## Requirements 
NXOS 9.3(6) to 9.3(7) via ND-ISSU

Pyats 

Python 3+
