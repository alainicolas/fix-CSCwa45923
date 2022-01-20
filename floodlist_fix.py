import floodlist
import yaml
import jinja2
from genie.testbed import load
import argparse

#Main script file. Loading data and parameters.

parser = argparse.ArgumentParser(description='''Python script to check if a Nexus device is impacted with CSCwa45923 and to fix it if needed.
list_ip.yaml : 
List of ip you want to check.
testbed.tpl : 
Setup your testbed. 
Outputs folder : 
Will save data for broken devices.

Default behavior : Check for issues with console outputs.
''')
parser.add_argument("-s", "--silent", help="Run the script without any console output.", action="store_true")
parser.add_argument("-f", "--fix", help="Run the fix if an issue is found.", action="store_true")
parser.add_argument("-l", "--log", help="Log the output of each device in a text file.", action="store_true")

args = parser.parse_args()

with open("./templates/list_ip.yaml", "r") as file:
    list_ip = yaml.load(file, Loader=yaml.FullLoader)

# Where's the folder with my templates
template_loader = jinja2.FileSystemLoader(searchpath="./templates")

# Instance of the Environment class.
template_env = jinja2.Environment(loader=template_loader)

# Which file is my template
template = template_env.get_template("testbed.tpl")
testbed = load(template.render(list_ip_id = zip(list_ip, range(len(list_ip)))))

#Initializing the dummy peer list


# For each device in our testbed, except our Linux rebound server :
for device in testbed:
    if device.type != "linux":
        try:
            device.connect(learn_hostname=True,
                           init_exec_commands=[],
                           init_config_commands=[],
                           log_stdout=False)

            print(f'-- {device.hostname} --')
            dummy = "1616"
            #If we want to log ->
            if args.log:
                with open(f'./outputs/{device.hostname}.txt', 'w') as file:
                    #Checking if we have broken peers on this device
                    brokenpeers = floodlist.checkBrokenPeer(device)
                    if not brokenpeers:
                        if not args.silent:
                            print("Floodlist is OK.")
                        file.write('Floodlist is OK')
                        file.write('\n')
                    else:
                        if not args.silent:
                            print("Device is broken")
                            print("")
                        file.write('Device is broken')
                        file.write('\n\n')

                        #We found broken peers. Generating a Peers per VNI DB and a VLAN to VNI DB
                        dbvni = floodlist.dbVni(device)
                        dbvlan = floodlist.dbVlan(device)

                        for peer in brokenpeers:
                            #For each broken peer, check all VNI where the peer is wrongly programmed
                            #And add it to vniList

                            vniList = floodlist.brokenPeerVni(device, peer, dbvlan, dbvni, dummy)
                            if not args.silent:
                                print("This peer is broken : " + peer)
                            file.write("This peer is broken : " + peer)
                            file.write('\n')
                            if not args.silent:
                                print("VNI to fix : ")
                            file.write("VNI to fix : ")
                            file.write('\n')
                            for vni in vniList:
                                if not args.silent:
                                    print(str(vni[0]))
                                file.write(str(vni))
                                file.write('\n')

                            #If --fix, we will fix these VNIs for this specific peer.
                            if args.fix:
                                #This will add then remove the peer on the wrongly programmed VNI.
                                floodlist.fixBrokenPeer(device, peer, vniList,dbvlan)
                                if not args.silent:
                                    print(str(peer) + " Fixed")
                                    print("")
                                file.write(str(peer) + " Fixed")
                                file.write('\n')
                                file.write('\n')

                    print("Done.")
                    print("")
                    file.write("Done.")
                    file.write('\n')

            #If we dont wan't to log ->
            else:
                    # Checking if we have broken peers on this device
                    brokenpeers = floodlist.checkBrokenPeer(device)
                    if not brokenpeers:
                        if not args.silent:
                            print("Floodlist is OK.")
                    else:
                        if not args.silent:
                            print("Device is broken")

                        # We found broken peers. Generating a Peers per VNI DB and a VLAN to VNI DB
                        dbvni = floodlist.dbVni(device)
                        dbvlan = floodlist.dbVlan(device)


                        for peer in brokenpeers:
                           # For each broken peer, check all VNI where the peer is wrongly programmed
                           # And add it to vniList

                           vniList = floodlist.brokenPeerVni(device, peer, dbvlan, dbvni, dummy)
                           if not args.silent:
                                print("This peer is broken : " +peer)
                                print("VNI to fix : ")
                                for vni in vniList:
                                    print(str(vni[0]))


                           # If --fix, we will fix these VNIs for this specific peer.
                           if args.fix :
                               # This will add then remove the peer on the wrongly programmed VNI.
                               floodlist.fixBrokenPeer(device, peer, vniList, dbvlan)
                               if not args.silent:
                                    print(str(peer) + " Fixed")
                                    print("")

                    print("Done.")
                    print("")

        except ValueError:
            print("Cannot connect to :")
            print(f'-- {device.hostname} --')
