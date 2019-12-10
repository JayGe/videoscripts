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
FEC="2/3"
FECNUM,FECDEN=FEC.split("/")
GAIN=-20
FREQ="2407.75"
MODE="DVBS2"
overlay=""
keyint=500
audiobitrate=24000
#audiobitrate=14000
res="1024x576"

correc=980
Me=2

videosource="~/myvideo.mkv"
#videosource="rtmp://127.0.0.1/live/obs"

#plutoScriptFile="pluto.sh" # TODO: add script parameter option, add file check

plutoServer="192.168.2.17" # TODO: merge with listenip
plutoUsername="root"
plutoPassword="analog"

mqttServer="192.168.0.201"

obsServer="localhost" # TODO: add script parameter option
obsPort="4444"
obsPassword="whatever"

def usage():
	print("""
-s --sr Symbol Rate in kS 333 
-f --fec Fec : {1/2,3/4,5/6,7/8} for DVBS {1/4,1/3,2/5,1/2,3/5,2/3,3/4,5/6,7/8,8/9,9/10} for DVBS2
-q --freq Frequency 2409.25
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
		SR=arg
	if opt in ('-k', '--key'):
		keyint=int(arg)
	if opt in ('-f', '--fec'):
		FEC=arg		
#	if opt in ('-l', '--listen'):
#		LISTENIP=arg
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


# 2. temporary calculation 
Calculatebitrate = SR * 100 * Me * int(FECNUM) * correc / (int(FECDEN)* 100)

print "muxrate:", Calculatebitrate
vidrate = (Calculatebitrate - 50000 - audiobitrate * 125 /100) * 80 / 100
print "vidrate:", vidrate
BUFSIZE= vidrate * 40 / 100
print "bufsize:", BUFSIZE

plutoCommand=("nc -u -l -p 1234 | /root/pluto_dvb -m %s -c %s -s %s000 -f %s -t %se6 -g %s"%(MODE,CONSTEL,SR,FEC,FREQ,GAIN))

h264Command = ("ffmpeg -i %s %s -c:v libx264 -x264-params \"nal-hrd=cbr:force-cfr=1:keyint=%d\" -preset fast -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g 50 -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=%s -flush_packets 0 -f mpegts -async 1 -vsync 1 -"%(videosource,overlay,keyint,res,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,CALLSIGN)) #	 7 seconds, 6.7 preset fast

h264Command_nvenc = ("ffmpeg -i %s %s -c:v h264_nvenc -preset llhp -tune film -rc cbr_ld_hq -surfaces 2-profile:v high -g 999999 -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g %s -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=%s -flush_packets 0 -f mpegts -async 1 -vsync 1 -"%(videosource,overlay,res,keyint,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,CALLSIGN)) #  4.75 seconds fast 

#h264Command_nvenc = ("ffmpeg -i %s %s -c:v h264_nvenc -preset medium -rc cbr -profile:v high -bf 3 -temporal-aq 1 -rc-lookahead 20 -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g 50 -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=%s -flush_packets 0 -f mpegts -async 1 -vsync 1 -"%(videosource,overlay,res,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,CALLSIGN)) # 6 seconds

h265Command_nvenc = ("ffmpeg -hwaccel cuvid -i %s %s -c:v hevc_nvenc -preset llhp -tune film -rc cbr_ld_hq -surfaces 2 -forced-idr 1 -profile:v main -g 999999 -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g %s -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=%s -flush_packets 0 -f mpegts -async 1 -vsync 1 -"%(videosource,overlay,res,keyint,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,CALLSIGN)) # 3.5 seconds

# TODO select command with option
#finalCommand = ("%s | nc -u %s 1234"%(h264Command,plutoServer))
#finalCommand = ("%s | nc -u %s 1234"%(h264Command_nvenc,plutoServer))
finalCommand = ("%s | nc -u %s 1234"%(h265Command_nvenc,plutoServer))

print (finalCommand)
#exit()
def exit_handler(): # turn the amplifier off after a normal application close
    os.system("/usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'OFF'")

atexit.register(exit_handler)

# Watch the output
#def line_buffered(f):
#    line_buf = ""
#    while not f.channel.exit_status_ready():
#        line_buf += f.read(1).decode(encoding="utf-8")
#        if line_buf.endswith('\n'):
#             yield line_buf
#             line_buf = ''

if (runCom): # If runCom set, exeute the command and other options, else just display the script
	if (obsOn): # Uses OBS Websocket to turn Record on when we transmit, profile has to match 
		client = obswebsocket.obsws(obsServer, obsPort, obsPassword)
		client.connect()
		# TODO: Select/create appropriate profile as can't change stream/record options via the web API yet
		currentProfile=client.call(obswebsocket.requests.GetCurrentProfile())
		print("Current OBS Profile: %s"%currentProfile.datain['profile-name'])
		client.call(obswebsocket.requests.StartRecording())
		client.disconnect()
		time.sleep(1)
	if (ampOn): # turn the amplifier on in background after a suitable delay time
		os.system("(sleep 5; /usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'ON')&")

	ssh = paramiko.SSHClient() # SSH to pluto and run command
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
	ssh.connect(plutoServer, username=plutoUsername, password=plutoPassword)
	ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(plutoCommand)
	#for l in line_buffered(ssh_stdout):
	#	print (l)

	# Run ffmpeg | netcat 
	os.system(finalCommand)


else:
	print(plutoCommand)

exit(0) 
