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


def brokenPeerVni(device,peer,dbvlan,dbvni,dummy):
    #For a peer on a device, return a list of broken vni
    #This list will be used as parameter for the fixing function

    vniList = []

    # 1 List all the vlan from the running config
    configuredVlanList = vniListToVlan(vniPerPeer(dbvni, peer), dbvlan)

    # 2 List all the vlans setup for this specific peer.
    brokenVlanList = vlanPerBrokenPeer(device, peer)

    # 3 We want to find programmed vlan that are not in the running config.
    listdiff = diffList(brokenVlanList, configuredVlanList)

    # 4 Check if the vlan exist :
    #List of existing vlans :
    vlans = [a_tuple[0] for a_tuple in dbvlan]

    #For each vlan of the list
    for diff in listdiff:
        #if it exists, give the vni
        if str(diff) in vlans:

            vniList.append(vlanListToVni([str(diff)], dbvlan))

        #Else, append a dummy vni to vniList.
        else:
            # 1616 + missing VLAN is a dummy VNI unused by OVH.
            dummy_str = dummy + str(diff)

            dbvlan.append((str(diff), dummy_str))

            vniList.append(vlanListToVni([str(diff)], dbvlan))


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

def fixBrokenPeer(device,peer,vniList,dbvlan):
    #This function will add/remove the given peer for each VNI from the VNI List
    #It should fix the floodlist.

    #18 Janvier :
    #Verifier si le vlan existe. Si il n'existe pas le créer
    #Vérifier si ca marche pour plusieurs VNI dans "vniList"

    for vni in vniList:
        #Check which vlan is going to be updated
        #If its a dummy VNI, we need to create the dummy vlan
        myvni = str(vni[0])
        mypeer = str(peer)
        #If Dummy VLAN :




        ### Delete when ready :
        if str(vni[0])[0:-4] == "1616":
            myvlan = str(vni[0])[-4:]

            # Create Vlan
            print('''
                        vlan ''' + myvlan + '''
                         vn-segment ''' + myvni
                             )

            # Config Dummy VNI
            print('''
                        interface nve1
                         member vni ''' + myvni + '''
                        ingress-replication protocol static
                        peer-ip ''' + mypeer)
            # Delete the Dummy VNI
            print('''
                        interface nve1
                         no member vni ''' + myvni)

            # Delete VNI from VLAN
            print('''
                                    vlan ''' + myvlan + '''
                                     no vn-segment ''' + myvni
                  )

            # Else, classic configuration of the VNI
            # Do not delete the VNI
        else:

            print('''
                        interface nve1
                         member vni ''' + myvni + '''
                        ingress-replication protocol static
                        peer-ip ''' + mypeer)
            print('''
                        interface nve1
                         member vni ''' + myvni + '''
                        ingress-replication protocol static
                        no peer-ip ''' + mypeer)

        ### End of delete when ready


        #Uncomment when ready :
        """
        if str(vni[0])[0:-4] == "1616":
            myvlan = str(vni[0])[-4:]

            #Create Vlan
            device.configure('''
                vlan ''' + myvlan + '''
                 vn-segment ''' + myvni
                )

           #Config Dummy VNI
            device.configure('''
                interface nve1
                 member vni ''' + myvni + '''
                ingress-replication protocol static
                peer-ip ''' + mypeer)
            #Delete the Dummy VNI
            device.configure('''
                interface nve1
                 no member vni ''' + myvni)

            #Delete VNI from VLAN
            device.configure('''
                vlan ''' + myvlan + '''
                 no vn-segment ''' + myvni
                )

        #Else, classic configuration of the VNI
        #Do not delete the VNI
        else:

            device.configure('''
                interface nve1
                 member vni ''' + myvni + '''
                ingress-replication protocol static
                peer-ip ''' + mypeer)
            device.configure('''
                interface nve1
                 member vni ''' + myvni + '''
                ingress-replication protocol static
                no peer-ip ''' + mypeer)
        """
    return True