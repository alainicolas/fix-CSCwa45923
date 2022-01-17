#List of functions used by floodlist_fix.py

def dbVlan(device):
    #For a device, create a DB with matching VLAN and VNI.
    #Return the vni/vlan DB
    nve = device.parse("show nve vni")
    dbvlan = [(nve['nve1']['vni'][vni]['type'][4:-1], str(vni)) for vni in nve['nve1']['vni']]
    return dbvlan


def dbVni(device):
    #For a device, create a DB with matching VNI and Peers.
    #Return the VNI/peers DB
    nve = device.parse("show nve vni ingress-replication")
    dbvni = {}
    for vni in nve['nve1']['vni']:
        dbvni.setdefault(vni, [])
        # print("this is my vni", + vni)
        for ip in nve['nve1']['vni'][vni]['repl_ip']:
            dbvni[vni].append(ip)
    return dbvni


def vlanForVni(mydbvlan, vni):
    #Return a vlan for a VNI. VNI must be a string
    vlan = [x for (x, y) in mydbvlan if y == vni]
    return str(vlan[0])


def vniForVlan(mydbvlan, vlan):
    #Return a vlan for a VNI. VNI must be a string
    vni = [y for (x, y) in mydbvlan if x == vlan]
    return str(vni[0])


def checkBrokenPeer(device):
    #For a device, check if each peer belong to the right amount of vlans.
    #If not, append this peer to the broken peer list
    #Return the broken peer list
    vlan = device.execute("show nve peers | grep nve1 | exclude 0.0.0.0")
    peerdb = []
    brokenpeers = []

    for line in vlan.splitlines():
        peerdb.append(line.split()[1])

    for peer in peerdb:
        # CLI used :
        # sh forwarding internal nve vlan-floodlist | i 0xffffffff
        # sh forwarding nve l2 ingress-replication-peers | grep "peer :  x.x.x.x  marked" | count
        peercount = device.execute(
            "sh forwarding nve l2 ingress-replication-peers | grep \"peer :  " + peer + "  marked\" | count")
        if peercount != "0":
            # sh forwarding nve l2 ingress-replication-peers ipv4 x.x.x.x | i "VLAN list" | exclude Resyn | exclude PSS
            vlancount = device.execute(
                "sh forwarding nve l2 ingress-replication-peers ipv4 " + peer + " | i \"VLAN list\" | exclude Resyn | exclude PSS")

            if vlancount[19:-2] != peercount:
                brokenpeers.append(peer)

    return brokenpeers


def brokenPeerVni(device,peer,dbvlan,dbvni):
    #For a peer on a device, return a list of broken vni
    #This list will be used as parameter for the fixing function

    # 1 List all the vlan from the running config
    configuredVlanList = vniListToVlan(vniPerPeer(dbvni, peer), dbvlan)

    # 2 List all the vlans setup for this specific peer.
    brokenVlanList = vlanPerBrokenPeer(device, peer)

    # 3 We want to find programmed vlan that are not in the running config.
    listdiff = diffList(brokenVlanList, configuredVlanList)

    # 4 Transform this list of VLANs in a list of VNIs
    vniList = vlanListToVni(listdiff, dbvlan)

    return vniList

def vniPerPeer(vlanDb,peer):
    #Return a list of VNI where a specific peer in configured
    vniList = []
    for vni in vlanDb:
        for peers in vlanDb[vni]:
            if peers == peer:
                vniList.append(vni)
    return vniList

def vlanPerBrokenPeer(device,peer):
    #Return a list of VLAN programmed for a peer in the floodlist
    dbvlan = []
    cli = "show forwarding nve l2 ingress-replication-peers ipv4 " +peer+ " | i \"PSS VL-\""
    nve = device.execute(cli)
    vlans = nve[11:].split(",")
    for vlan in vlans:
        if "-" in vlan:
            thisrange = [i for i in range(int(vlan.split("-")[0]), int(vlan.split("-")[1]) + 1)]
            for rangevlan in thisrange:
                dbvlan.append(rangevlan)
        else:
            dbvlan.append(int(vlan))
    return dbvlan

def diffList(brokenList,configuredVlanList):
    #Return a list of unwanted vlan setup in the floodlist
    #Also called the delta between vlan in the running conf and vlan programmed in the floodlist.
    return set(brokenList).difference(configuredVlanList)

def vniListToVlan(vniList,dbvlan):
    #Return a list of VLAN from a VNI list
    vlanList = []
    for vni in vniList:
        vlanList.append(int(vlanForVni(dbvlan, str(vni))))
    return vlanList

def vlanListToVni(vlanList,dbvlan):
    #Return a list of VNI from a VLAN list
    vniList = []
    for vlan in vlanList:
        vniList.append(int(vniForVlan(dbvlan, str(vlan))))
    return vniList

def fixBrokenPeer(device,peer,vniList):
    #This function will add/remove the given peer for each VNI from the VNI List
    #It should fix the floodlist.
    for vni in vniList:
        device.configure('''
            interface nve1
             member vni ''' + str(vni) + '''
            ingress-replication protocol static
            peer-ip ''' + str(peer))
        device.configure('''
            interface nve1
             member vni ''' + str(vni) + '''
            ingress-replication protocol static
            no peer-ip ''' + str(peer))
    return True