#!/usr/bin/python
import sys, getopt
import subprocess
import os

number_of_nodes = '200'
evaluation_time = '600'
GRID_ROW_SIZE = '10'
operation_str = 'none'
no_build_cache_docker = ''

base_container_name0 = 'mybaseubuntu'
base_container_name1 = 'myubuntu'
ns3_path = "/home/ubuntu/workspace/source/ns-3.25/"

pids_directory = "./var/pid/"
logs_directory = "./var/log/"


def check_return_code(r_code, log):
    """
    calls sys.exit in case of error
    :param r_code: code return by subprocess call
    :param log: String to be shown in console
    """
    if r_code != 0:
        print "Error: %s" % log
        sys.exit(2)
    else:
        print "Success: %s" % log
    return


def check_return_code_passive(r_code, log):
    """
    verfies r_code and prints error string str in case of error
    :param r_code: code return by subprocess call
    :param log: String to be shown in console
    """
    if r_code != 0:
        print "Error: %s" % log
    else:
        print "Success: %s" % log
    return


def run_docker_containers(dir_path):
    """
    runs the numberOfNodes of containers
    :param dir_path:
    """
    acc_status = 0
    for node in range(0, numberOfNodes):
        if not os.path.exists(logs_directory + nameList[node]):
            os.makedirs(logs_directory + nameList[node])

        logHostPath = dir_path + logs_directory[1:] + nameList[
        node]  # "." are not allowed in the -v of docker and it just work with absolute paths

        acc_status += subprocess.call("docker run --privileged -dit --net=none -v %s:/var/log/golang --name %s %s" % (
            logHostPath, nameList[node], base_container_name1), shell=True)

    check_return_code(acc_status, "Running docker containers")


def create_bridge_and_tap_interfaces():
    """
    creates the bridges and the tap interfaces for NS3
    """
    acc_status = 0
    for x in range(0, numberOfNodes):
        acc_status += subprocess.call("sudo bash net/singleSetup.sh %s" % (nameList[x]), shell=True)

    check_return_code(acc_status, "Creating bridge and tap interface")

    acc_status += subprocess.call("sudo bash net/singleEndSetup.sh", shell=True)
    check_return_code(acc_status, "Finalizing bridges and tap interfaces")


def create_bridge_for_containers():
    acc_status = 0
    for x in range(0, numberOfNodes):
        cmd = ['docker', 'inspect', '--format', "'{{ .State.Pid }}'", nameList[x]]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        pid = out[1:-2].strip()

        with open(pids_directory + nameList[x], "w") as text_file:
            text_file.write("%s" % (pid))

        acc_status += subprocess.call("sudo bash net/container.sh %s %s" % (nameList[x], x), shell=True)

    # If something went wrong creating the bridges and tap interfaces, we panic and exit
    check_return_code(acc_status, "Creating bridge side-int-X and side-ext-X")


def run_code_in_ns3():
    r_code = subprocess.call("cd ns3 && cp tap-wifi-virtual-machine.cc %s" % ns3_path+"/scratch/tap-vm.cc", shell=True)
    if r_code != 0:
        print "Error copying latest ns3 file"
    else:
        print "NS3 up to date!"
        print "Go to NS3 folder, probably cd $NS3_HOME"
        print "Run sudo ./waf --run \"scratch/tap-vm --NumNodes=%s --TotalTime=%s --TapBaseName=emu\"" % (
            number_of_nodes, evaluation_time)
        print "or run sudo ./waf --run \"scratch/tap-vm --NumNodes=%s --TotalTime=%s --TapBaseName=emu --SizeX=100 --SizeY=100\"" % (
            number_of_nodes, evaluation_time)

    print "Done."


def create():
    print "Creating ..."

    validate_ubuntu_version()

    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    run_docker_containers(dir_path)

    create_bridge_and_tap_interfaces()

    if not os.path.exists(pids_directory):
        os.makedirs(pids_directory)

    create_bridge_for_containers()

    run_code_in_ns3()

    return


def ns3():
    print "NS3 ..."

    r_code = subprocess.call(
        "cd $NS3_HOME && sudo ./waf --run \"scratch/tap-vm --NumNodes=%s --TotalTime=%s --GridRowSize=%s --TapBaseName=emu\"" % (
            number_of_nodes, evaluation_time, GRID_ROW_SIZE), shell=True)
    if r_code != 0:
        print "NS3 WIN!"
    else:
        print "NS3 FAIL!"

    return


def validate_ubuntu_version():
    """makes sure that we are running the latest version of our Ubuntu container, as we need some tools available in
    latest version only.
    """
    r_code = subprocess.call("docker build -t %s docker/mybase/." % base_container_name0, shell=True)
    check_return_code(r_code, "Building base container %s" % base_container_name0)

    r_code = subprocess.call("docker build %s -t %s docker/myubuntu/." % (no_build_cache_docker, base_container_name1),
                             shell=True)
    check_return_code(r_code, "Building regular container %s" % base_container_name1)


def destroy():
    print "Destroying ..."

    for x in range(0, numberOfNodes):
        r_code = subprocess.call("docker stop -t 0 %s" % (nameList[x]), shell=True)
        check_return_code_passive(r_code, "Stopping docker container %s" % (nameList[x]))

        r_code = subprocess.call("docker rm %s" % (nameList[x]), shell=True)
        check_return_code_passive(r_code, "Removing docker container %s" % (nameList[x]))

        r_code = subprocess.call("sudo bash net/singleDestroy.sh %s" % (nameList[x]), shell=True)
        check_return_code_passive(r_code, "Destroying bridge and tap interface %s" % (nameList[x]))

        if os.path.exists(pids_directory + nameList[x]):
            with open(pids_directory + nameList[x], "rt") as in_file:
                text = in_file.read()
                r_code = subprocess.call("sudo rm -rf /var/run/netns/%s" % (text.strip()), shell=True)
                check_return_code_passive(r_code, "Destroying docker bridges %s" % (nameList[x]))

        r_code = subprocess.call("sudo rm -rf %s" % (pids_directory + nameList[x]), shell=True)

    return


###############################
# n == number of nodes
# t == simulation time in seconds
###############################
# Cache an error with try..except
# Note: options is the string of option letters that the script wants to recognize, with
# options that require an argument followed by a colon (':') i.e. -i fileName
#
try:
    myopts, args = getopt.getopt(sys.argv[1:], "hn:o:t:p:", ["number=", "operation=", "time=", "no-cache","path"])
except getopt.GetoptError as e:
    print (str(e))
    print("Usage: %s -o <create|destroy> -n numberOfNodes -t emulationTime" % sys.argv[0])
    sys.exit(2)

for opt, arg in myopts:
    if opt == '-h':
        print("Usage: %s -o <create|destroy> -n numberOfNodes -t emulationTime -p ns3Home" % sys.argv[0])
        sys.exit()
    elif opt in ("-n", "--number"):
        number_of_nodes = arg
    elif opt in ("-t", "--time"):
        evaluation_time = arg
    elif opt in ("-p", "--path"):
        ns3_path = arg
    elif opt in ("-o", "--operation"):
        operation_str = arg
    elif opt in ("--no-cache"):
        no_build_cache_docker = '--no-cache'

# Display input and output file name passed as the args
print (
    "Number of nodes : %s and emulation time : %s and operation : %s" % (
        number_of_nodes, evaluation_time, operation_str))

numberOfNodes = int(number_of_nodes)
emulationTime = int(evaluation_time)

nameList = []
baseName = "emu"

for x in range(0, numberOfNodes):
    nameList.append(baseName + str(x + 1))

if 'create' == operation_str:
    create()
elif 'destroy' == operation_str:
    destroy()
elif 'full' == operation_str:
    create()
    ns3()
    destroy()
else:
    print "Nothing to be done ..."
