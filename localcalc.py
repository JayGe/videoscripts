#!/usr/bin/python
# Python wrapper for ffmpeg + limesdr_dvb

import sys,getopt,os,time
import shlex
from subprocess import Popen, PIPE
import atexit

#default settings, change the first three, the rest can be set to preference and changed in command parameters

callsign="GI7UGV"
dvbsdrloc="/home/r/radio/video/dvbsdr/bin/limesdr_dvb"
#dvbsdrloc="/home/pi/dvbsdr/bin/limesdr_dvb"
videosource="~/myvideo.mkv"
#videosource="rtmp://127.0.0.1/live/obs"

ffmpegloc=""
overlay=""
runcom=0
obson=0
ampon=0
SR=333
#correc=980
#Me=2
Alterbitrate=20000
FECNUM=2
FECDEN=3
UPSAMPLE=2
MODE="DVBS2"
CONST="QPSK"
TYPEFRAME="-v" # add params opt
PILOTS=""
FREQ="2409.25e6" 
GAIN="0.79"
FPGAMODE="" # add params opt
#audiobitrate=24000
audiobitrate=14000
res="1024x576"
#res="640x360"
keyint=500

def usage():
	print("""
-s --sr Symbol Rate in kS 333 
-f --fec Fec : {1/2,3/4,5/6,7/8} for DVBS {1/4,1/3,2/5,1/2,3/5,2/3,3/4,5/6,7/8,8/9,9/10} for DVBS2
-r --res Resolution 640x360
-q --freq Frequency 2409.25e6
-g --gain Lime Gain 79
-v --video Video Source
-c --const Constellation mapping (DVBS2) : {QPSK,8PSK,16APSK,32APSK}
-1 --dvbs Set DVB-S Default DVB-S2
-k --key Set key int 500
-e --exec Execute the generated command
-o --obs Turn OBS recording on
-a --amp Turn amplifier on via mqtt
-p --pilots Turn pilots on
-y --overlay Turns callsign text overlay on
""")

try:
	opts, args = getopt.getopt(sys.argv[1:], 's:k:f:r:c:1eg:q:pv:oayh', ['sr=', 
                                                   'key=',
                                                   'fec=',
                                                   'res=',
                                                   'const=',
                                                   'dvbs', 
                                                   'exec',
												   'gain',
												   'freq',
												   'pilots',
                                                   'video',
												   'obson',
												   'ampon',
												   'overlay',
												   'help',
                                                   ])
except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)

for opt, arg in opts:
	if opt in ('-s', '--sr'):
		SR=int(arg)
	if opt in ('-k', '--key'):
		keyint=int(arg)
	if opt in ('-f', '--fec'):
		FECNUM,FECDEN=arg.split("/")
	if opt in ('-r', '--res'):
		res=arg
	if opt in ('-v', '--video'):
		videosource=arg
	if opt in ('-p', '--pilots'):
		PILOTS="-p"
	if opt in ('-g', '--gain'):
		GAIN="0."+arg
	if opt in ('-q', '--freq'):
		FREQ=arg#+"e6"
	if opt in ('-c', '--const'):
		#Me=3
		CONST=arg
	if opt in ('-e', '--exec'):
		runcom=1
	if opt in ('-o', '--obs'):
		obson=1
		import obswebsocket, obswebsocket.requests
	if opt in ('-a', '--amp'):
		ampon=1
	if opt in ('-y', '--overlay'):
		overlay=("-vf \"drawtext=fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf':text='%s':x=34:y=34:fontsize=64:fontcolor=0xffffff7f:shadowcolor=0x003f007f:shadowx=2:shadowy=2\""%(callsign))
	if opt in ('-1', '--dvbs'):
		#correc=922
		MODE="DVBS"
	if opt in ('-h', '--help'):
		usage()
		sys.exit(0)

SRL=str(SR)+"000"

print ("SR=%d FEC=%s/%s MODE=%s CONST=%s Res=%s"% (SR, FECNUM, FECDEN, MODE, CONST, res))

def exit_handler(): # turn the amplifier on after a normal application close
    os.system("/usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'OFF'")

atexit.register(exit_handler)

command = ("%s -d -s %s -f %s/%s -r %d -m %s -c %s %s %s -t %s -g %s -q 1 %s"%(dvbsdrloc,SRL,FECNUM,FECDEN,UPSAMPLE,MODE,CONST,TYPEFRAME,PILOTS,FREQ,GAIN,FPGAMODE))
process = Popen(shlex.split(command), stdout=PIPE)
(output, err) = process.communicate()
exit_code = process.wait()
Calculatebitrate = int(output.rstrip())

# copied bits from windows batch file from Feb 2019 Evariste F5OEO

#Calculatebitrate = SR * 100 * Me * int(FECNUM) * correc / (int(FECDEN)* 100)

Calculatebitrate = Calculatebitrate + Alterbitrate
print "muxrate:", Calculatebitrate
vidrate = (Calculatebitrate - 50000 - audiobitrate * 125 /100) * 80 / 100
print "vidrate:", vidrate
BUFSIZE= vidrate * 40 / 100
print "bufsize:", BUFSIZE

command2 = ("ffmpeg -i %s %s -c:v libx264 -x264-params \"nal-hrd=cbr:force-cfr=1:keyint=%d\" -preset slow -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g 50 -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=%s -flush_packets 0 -f mpegts -async 1 -vsync 1 - | %s -s %s -f %s/%s -r %d -m %s -c %s %s %s -t %s -g %s -q 1 %s"%(videosource,overlay,keyint,res,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,callsign,dvbsdrloc,SRL,FECNUM,FECDEN,UPSAMPLE,MODE,CONST,TYPEFRAME,PILOTS,FREQ,GAIN,FPGAMODE))

print (command2)

if (runcom):
	if (obson): # Uses OBS Websocket to turn Record on when we transmit
		client = obswebsocket.obsws("localhost", 4444, "whatever")
		client.connect()
		client.call(obswebsocket.requests.StartRecording())
		client.disconnect()
		time.sleep(1)
	if (ampon): # turn the amplifier on in background after a suitable delay time to avoid sending nasties
		os.system("(sleep 7; /usr/bin/mosquitto_pub -h 192.168.0.201 -t '/radio/amp/set2' -m 'ON')&")
	os.system(command2)
	

