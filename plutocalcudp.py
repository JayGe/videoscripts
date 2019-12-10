#!/usr/bin/python
# Python wrapper for executing pluto_sdr on UDP input via SSH, turning OBS on & turning amplifier on

import sys,getopt,os,time
import atexit
import paramiko

runCom=1 # run the command by default
obsOn=0 # doesn't turn OBS on by default 
ampOn=0 # doesn't turn Amplifier on by default TODO: add mqtt server variables

TYPEFRAME="-v" # TODO: add option to shell script
PILOTS="" # TODO: add option to shell script

CALLSIGN="GI7UGV"
CONSTEL="QPSK"
SR=333
FEC=23
GAIN=-20
FREQ="2409.25"
MODE="DVBS2"
LISTENIP="udp://192.168.2.17:8282/"

plutoScriptFile="pluto.sh" # TODO: add script parameter option, add file check

plutoServer="192.168.2.17" # TODO: merge with listenip
plutoUsername="root"
plutoPassword="analog"


#obsServer="192.168.0.54" # TODO: add script parameter option
obsServer="localhost"
obsPort="4444"
obsPassword="whatever"

def usage():
	print("""
-s --sr Symbol Rate in kS 333 
-f --fec Fec : {1/2,3/4,5/6,7/8} for DVBS {1/4,1/3,2/5,1/2,3/5,2/3,3/4,5/6,7/8,8/9,9/10} for DVBS2
-q --freq Frequency 2409.25e6
-g --gain Pluto Gain (-71..0) Default -20
-l --listen Listen Source (udp://192.168.2.17:8282/
-c --const Constellation mapping (DVBS2) : {QPSK,8PSK,16APSK,32APSK}
-1 --dvbs Set DVB-S Default DVB-S2
-k --key Set key int 500 # REMOVE
-d --disp Display the generated script, dont run
-o --obs Turn OBS recording on
-a --amp Turn amplifier on via MQTT
-p --pilots Turn pilots on
-y --overlay Turns callsign text overlay on # REMOVE
""")

try:
	opts, args = getopt.getopt(sys.argv[1:], 's:k:f:c:1dg:q:pl:oayh', ['sr=', 
                                                   'key=',
                                                   'fec=',
                                                   'const=',
                                                   'dvbs', 
                                                   'disp',
												   'gain',
												   'freq',
												   'pilots',
                                                   'listen',
												   'obson',
												   'ampon',
												   'overlay',
												   'help',
                                                   ])
except getopt.GetoptError as err:
        print (str(err))
        usage()
        sys.exit(2)

for opt, arg in opts:
	if opt in ('-s', '--sr'):
		SR=int(arg)
	if opt in ('-k', '--key'):
		keyint=int(arg)
	if opt in ('-f', '--fec'):
		FECNUM,FECDEN=arg.split("/")
		FEC=int(FECNUM+FECDEN)
	if opt in ('-l', '--listen'):
		LISTENIP=arg
	if opt in ('-p', '--pilots'):
		PILOTS="-p"
	if opt in ('-g', '--gain'):
		GAIN=arg
	if opt in ('-q', '--freq'):
		FREQ=arg
	if opt in ('-c', '--const'):
		CONSTEL=arg
	if opt in ('-d', '--disp'):
		runCom=0
	if opt in ('-o', '--obs'):
		obsOn=1
		import obswebsocket, obswebsocket.requests
	if opt in ('-a', '--amp'):
		ampOn=1
	if opt in ('-y', '--overlay'):
		overlay=("-vf \"drawtext=fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf':text='%s':x=34:y=34:fontsize=64:fontcolor=0xffffff7f:shadowcolor=0x003f007f:shadowx=2:shadowy=2\""%(CALLSIGN))
	if opt in ('-1', '--dvbs'):
		MODE="DVBS"
	if opt in ('-h', '--help'):
		usage()
		sys.exit(0)

with open (plutoScriptFile, "r") as myfile:
    plutoScript=myfile.read()

plutoConfig=("CALL=%s\nCONSTEL=%s\nSR=%d\nFEC=%s\nGAIN=%s\nFREQ=%s\nMODE=%s\nLISTENIP=%s\n"%(CALLSIGN,CONSTEL,SR,FEC,GAIN,FREQ,MODE,LISTENIP))

plutoCommand=plutoConfig+plutoScript

def exit_handler(): # turn the amplifier off after a normal application close
    os.system("/usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'OFF'")

atexit.register(exit_handler)

# Watch the output
def line_buffered(f):
    line_buf = ""
    while not f.channel.exit_status_ready():
        line_buf += f.read(1).decode(encoding="utf-8")
        if line_buf.endswith('\n'):
             yield line_buf
             line_buf = ''

if (runCom): # If runCom set, exeute the command and other options, else just display the script
	if (obsOn): # Uses OBS Websocket to turn Record on when we transmit, profile has to match 
		client = obswebsocket.obsws(obsServer, obsPort, obsPassword)
		client.connect()
		# TODO: Select/create appropriate profile as can't change stream/record options via the web API
		currentProfile=client.call(obswebsocket.requests.GetCurrentProfile())
		print("Current OBS Profile: %s"%currentProfile.datain['profile-name'])
		client.call(obswebsocket.requests.StartRecording())
		client.disconnect()
		time.sleep(1)
	if (ampOn): # turn the amplifier on in background after a suitable delay time
		os.system("(sleep 5; /usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'ON')&")
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
	ssh.connect(plutoServer, username=plutoUsername, password=plutoPassword)
	ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(plutoCommand)

	for l in line_buffered(ssh_stdout):
		print (l)
else:
	print(plutoCommand)

exit(0) 
