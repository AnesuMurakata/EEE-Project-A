from time import sleep
import time
import spidev
import RPi.GPIO as GPIO
import BlynkLib 
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 200000

# Variables
buttons = (7,11,36,37)				# 7-changing reading interval, 11-Reset system time, 36-Dismiss alarm, 37-Start/Stop Monitoring
outputs = (0,1) # to be set
pressCount = 0
readingFrequency = 1				# At start of program the default reading frequeny is 1 second
start = False
starty = time.time()
alarmt = time.time()
flag = True
blynk_auth = "4hj_ax-w30qvSowJ7svz1Rt2i9B6RZUt"
blynk = BlynkLib.Blynk(blynk_auth)
delay = 5

@blynk.VIRTUAL_WRITE(1)
def my_write_handler(value):
    global delay
    delay = int(value[0])
    #print('Current delay value: {}'.format(delay))

while(1):
    blynk.run()


def LDR():
	cbyte = 0b10000000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	return x

def humidity_Sensor():
	cbyte = 0b10010000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	voltage = round(((x*3.3)/1024),1)	# Humidity vloltage
	return voltage


def temperature_Sensor():
	cbyte = 0b10100000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	voltage = (x*3.3)/1024				# temperature vloltage
	temp_Ambient = int((voltage-0.4)/0.0195)	# Ambient temperature
	return temp_Ambient

def DAC():
	vout = round((LDR()*humidity_Sensor())/1023,1)
	return vout


def timer_string():
    global starty
    now = time.time() - starty

    m,s = divmod(now,60)
    h,m = divmod(m,60)

   
    timer_str = "%02d:%02d:%02d"%(h,m,s)
    psec = str(now - int(now))
    pstr = psec[1:5]
    timer_str = timer_str + str(pstr)

    return timer_str

def RTC_time():
	rtc = time.localtime()
	current_time = time.strftime("%H:%M:%S", rtc)
	return current_time

print("Press red button to start logging")

def GPIOsetup():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setwarnings(False)
	GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	#GPIO.setup(outputs, GPIO.OUT)
def changeInterval(channel):
	global pressCount
	global readingFrequency
	if pressCount == 0:
		readingFrequency = 2
		pressCount = pressCount + 1
	elif pressCount == 1:
		readingFrequency = 5
		pressCount = pressCount + 1
	else :
		readingFrequency = 1
		pressCount = 0

def resetSystemTime(channel):
    global starty
    global flag
    flag = True
    starty = time.time()

def dismissAlarm(channel):
	count = 2
star = " "
def fireAlarm():
    global alarmt
    global flag
    global star
    val = DAC()
    if(val < 0.65 or val > 2.65):
        if(flag):
            alarmt = time.time()
            flag = False
            star="*"
        
        
        current = time.time()
        duration = current - alarmt
        m,s = divmod(duration,60)
        if(m >= 1):
            alarmt = time.time()
            star= "*"
    else:
        star = " "
    return star
    
def monitoring(channel):
	global start
	if start:
		start = False
	else :
		start = True

print("-----------------------------------------------------------------")
print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format("RTC Time", "Sys Timer", "Humidity", "Temp","Light","DAC out","Alarm"))
print("-----------------------------------------------------------------")

GPIOsetup()
GPIO.add_event_detect(37, GPIO.FALLING, callback=changeInterval, bouncetime=400)
GPIO.add_event_detect(11, GPIO.FALLING, callback=resetSystemTime, bouncetime=400)
GPIO.add_event_detect(36, GPIO.FALLING, callback=dismissAlarm, bouncetime=400)
GPIO.add_event_detect(7, GPIO.FALLING, callback=monitoring, bouncetime=400)

def main():
	if start:
		print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format(RTC_time(), str(timer_string()),str(humidity_Sensor())+" V",str(temperature_Sensor())+" C",str(LDR()),str(DAC())+" V",str(fireAlarm())))
		sleep(readingFrequency)

if __name__ == "__main__":
	try:
		while True:
			main()
	except KeyboardInterrupt:
		print("Exiting gracefully")
		spi.close()

	finally:					# run on exit
		spi.close()				# clean up
		
		print("\n All cleaned up")

