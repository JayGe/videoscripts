mkfifo /root/bigtspipe
mkfifo /root/tspipe

while :
do
killall udpts.sh 2> /dev/null
killall ffmpeg 2> /dev/null
killall ffmpeg 2> /dev/null
rm infoudp
VIDEORATE=""
PCRPTS=2000
UDPIP=230.0.0.2:10000

#CALL=GI7UGV
#CONSTEL=QPSK
#SR=1000
#FEC=23
#GAIN=-10
#FREQ=2406.75
#MODE=DVBS2
#LISTENIP=udp://192.168.2.17:8282/

echo $CALL $MODE $CONSTEL $SR $FEC $GAIN $FREQ $LISTENIP
 (ffmpeg -analyzeduration 4000000 -ss 2 -f mpegts -i $LISTENIP -c:v copy -c:a copy -f mpegts -y /root/bigtspipe 2>infoudp ) &
PIDFFMPEG=$!
echo $PIDFFMPEG
while [ "$VIDEORATE" == "" ]
do
 
 sleep 1

 VIDEORATE=$(grep -o " Video:.*" infoudp | cut -f4 -d, | cut -f1 -d'k') 
 echo Wait for UDP connexion
done

#FREQ=$(grep -o "match up:.*" infoudp | cut -f2 -d,)
VIDEORES=$(grep -o "Stream #0:1:.*" infoudp | cut -f3 -d,) 

echo $VIDEORATE $VIDEORES 

#MODE=$(grep -o "match up:.*" infortmp | cut -f3 -d,)
#CONSTEL=$(grep -o "match up:.*" infortmp | cut -f4 -d,)
#SR=$(grep -o "match up:.*" infortmp | cut -f5 -d,)
#FEC=$(grep -o "match up:.*" infortmp | cut -f6 -d,)
#GAIN=$(grep -o "match up:.*" infortmp | cut -f7 -d,)

echo FREQ $FREQ MODE $MODE CONSTEL $CONSTEL SR $SR FEC $FEC

#CALL=$(grep -o "Unexpected stream.*" infortmp | cut -f2 -d,)
#IP=$(grep -o "Unexpected stream.*" infortmp | cut -f3 -d,)


if [ "$IP" = "" ]; then
        echo No debug IP
else
echo ip $IP
UDPIP=$IP
fi


TSBITRATE=$(/root/pluto_dvb -m $MODE -c $CONSTEL -s $SR"000" -f $FEC -d)
echo TsBitrate $TSBITRATE   	

VIDEOMAX=$(echo "($TSBITRATE/1000)*80/100" | bc)

if [[ "$VIDEORATE" -ge "$VIDEOMAX" ]] ; then
MESSAGE="V!$VIDEOMAX kb"
else
MESSAGE="V$VIDEORATE kb"
fi

if [ "$MODE" = "ANA" ]; then
        echo Analogique
echo 0 > /sys/bus/iio/devices/iio:device1/out_voltage_filter_fir_en
echo 2250000 > /sys/bus/iio/devices/iio:device1/out_voltage_sampling_frequency
echo $FREQ"000000" > /sys/bus/iio/devices/iio:device1/out_altvoltage1_TX_LO_frequency
ffmpeg -analyzeduration 4000000 -f flv -i /root/bigtspipe -c:v copy -c:a copy -f mpegts -y /root/tspipe \
| /root/hacktv -m apollo-fsc-fm -o - -t int16 -s 2250000 ffmpeg:/root/tspipe | iio_writedev -b 100000 cf-ad9361-dds-core-lpc
else
        echo DVB
ffmpeg -f mpegts -i /root/bigtspipe -ss 1 -c:v copy -c:a copy -muxrate $TSBITRATE -f mpegts -metadata service_provider="$MESSAGE" -metadata service_name=$CALL -streamid 0:256 -f tee -map 0:v -map 0:a "[f=mpegts:muxrate="$TSBITRATE":max_delay="$PCRPTS"000]/root/tspipe|[f=mpegts:muxrate="$TSBITRATE":max_delay="$PCRPTS"000]udp://"$UDPIP"?pkt_size=1316]" &
/root/pluto_dvb -i /root/tspipe -m $MODE -c $CONSTEL -s $SR"000" -f $FEC -t $FREQ"e6" -g $GAIN
fi
echo endstreaming
kill -9 $PIDFFMPEG
done

