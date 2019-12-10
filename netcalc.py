#!/usr/bin/python
# copied bits from windows batch file from Feb 2019 Evariste F5OEO - QO-100 Release 0.9

import sys,getopt,os,time
import obswebsocket, obswebsocket.requests

runcom=0
SR=333
correc=980
#correc=967
Me=2
FECNUM=2
FECDEN=3
audiobitrate=24000
res="1024x576"
res="640x360"
keyint=200

opts, args = getopt.getopt(sys.argv[1:], 's:k:f:r:81e', ['sr=', 
                                                   'key=',
                                                   'fec=',
                                                   'res=',
                                                   '8psk=',
                                                   'dvbs', 
                                                   'exec',
                                                   ])

for opt, arg in opts:
	if opt in ('-s', '--sr'):
		SR=int(arg)
	if opt in ('-k', '--key'):
		keyint=int(arg)
	if opt in ('-f', '--fec'):
		FECNUM,FECDEN=arg.split("/")
	if opt in ('-r', '--res'):
		res=arg
	if opt in ('-8', '--8psk'):
		Me=3
	if opt in ('-e', '--exec'):
		runcom=1
	if opt in ('-1', '--dvbs'):
		correc=922

print ("SR=%d FEC=%s/%s Me=%d"% (SR, FECNUM, FECDEN, Me))

Calculatebitrate = SR * 100 * Me * int(FECNUM) * correc / (int(FECDEN)* 100)

print "muxrate:", Calculatebitrate
vidrate = (Calculatebitrate - 50000 - audiobitrate * 125 /100) * 80 / 100
print "vidrate:", vidrate
BUFSIZE= vidrate * 40 / 100
print "bufsize:", BUFSIZE

#command = ("ffmpeg -i ~/myvideo.mkv -c:v libx264 -x264-params \"nal-hrd=cbr:force-cfr=1:keyint=%d \" -tune film -preset slower -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g 50 -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=GI7UGV -flush_packets 0 -f mpegts udp://192.168.2.19:10000"%(res,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate))
command = ("ffmpeg -i ~/myvideo.mkv -c:v libx264 -x264-params \"nal-hrd=cbr:force-cfr=1:keyint=%d\" -preset slow -pix_fmt yuv420p -r 25 -s %s -qmin 2 -qmax 50 -g 50 -b:v %d -minrate %d -maxrate %d -bufsize %d -muxrate %d -c:a aac -b:a 24000 -ar 48000 -ac 1 -f mpegts -mpegts_original_network_id 1 -mpegts_transport_stream_id 1 -mpegts_service_id 1 -mpegts_pmt_start_pid 4096 -streamid 0:256 -metadata service_provider=\"DATV\" -metadata service_name=GI7UGV -flush_packets 0 -f mpegts udp://192.168.2.19:10000?pkt_size=1316&bitrate=%d"%(keyint,res,vidrate,vidrate,vidrate,BUFSIZE,Calculatebitrate,Calculatebitrate))
print (command)

if (runcom):
	client = obswebsocket.obsws("localhost", 4444, "whatever")
	client.connect()
	client.call(obswebsocket.requests.StartRecording())
	client.disconnect()
	time.sleep(1)
	os.system(command)
	

