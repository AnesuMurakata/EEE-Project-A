from time import sleep

import threading
import time
import spidev
import RPi.GPIO as GPIO
import blynklib
from thread import Thread
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
BLYNK_AUTH = 'Lt3HiTyqL6WQtT-JotYQvnmpT8kUD3oc'

delay = 5
ringing = "No"
#@blynk.virtual_write(1)

# initialize blynk
blynk = blynklib.Blynk(BLYNK_AUTH)
    
READ_PRINT_MSG = "[READ_VIRTUAL_PIN_EVENT] Pin: V{}"
WRITE_EVENT_PRINT_MSG = "[WRITE_VIRTUAL_PIN_EVENT] Pin: V{} Value: '{}'"


def AlertLED():
        global ringing
        
        
        
        GPIO.output(13, GPIO.LOW)  # Set pin to low(0V)
        p = GPIO.PWM(13, 1000)     # set Frequece to 1KHz
        p.start(0)                     # Start PWM output, Duty Cycle = 0

        try:
                while(True):
                    if(ringing == "Yes"):
                        
                        for dc in range(0, 101, 5):   # Increase duty cycle: 0~100
                                p.ChangeDutyCycle(dc)     # Change duty cycle
                                time.sleep(0.05)
                        time.sleep(1)
                        for dc in range(100, -1, -5): # Decrease duty cycle: 100~0
                                p.ChangeDutyCycle(dc)
                                time.sleep(0.05)
                        time.sleep(1)
        except KeyboardInterrupt:
                p.stop()
                GPIO.output(LedPin, GPIO.HIGH)    # turn off all leds
                GPIO.cleanup()
            
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

print("Press start button to start logging")

def GPIOsetup():
    
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(13, GPIO.OUT, initial=GPIO.LOW) # Set pin 13 to be an output pin and set initial value to low (off)
    #GPIO.setup(outputs, GPIO.OUT)
    #trd = Thread("No")
    #trd = Thread("Yes")
    


    
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
    global flag
    global star
    global ringing
    flag = False
    ringing = "No"
    star = " "

    
def fireAlarm():
    global alarmt
    global flag
    global star
    global ringing
    global trd
    val = DAC()
    if(val < 0.65 or val > 2.65):
        if(flag):
            alarmt = time.time()
            flag = False
            star="*"
            ringing = "Yes"
            #blinking()
            #trd.notify()
        
        
        current = time.time()
        duration = current - alarmt
        m,s = divmod(duration,60)
        if(m >= 3):
            alarmt = time.time()
            star= "*"
            ringing = "Yes"
            #blinking()
            #trd.notify()
    else:
        star = " "
        ringing = "No"
        #notBlinking()
        
        
    return star

def my_user_task():
    #blynk.virtual_write(2,'{:.2f}'.format(temperature_sensor()))
    #blynk.virtual_write(3,'{:.2f}'.format(humidity_sensor()))
    c = 1+1
    

def monitoring(channel):
    global start
    if start:
        start=False
    else:
        start=True

@blynk.handle_event('write V4')
def write_virtual_pin_handler(pin, value):
    global start
    if(value > 0.5):
        start = True
        blynk.virtual_write(11, temperature_Sensor())
        blynk.virtual_write(10, LDR())
        blynk.virtual_write(12, humidity_Sensor())
    else:
        start = False
    
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))

# register handler for virtual pin V11 reading
@blynk.handle_event('read V11')
def read_virtual_pin_handler(pin):
    #print(READ_PRINT_MSG.format(pin))
    global start
    global ringing
    blynk.virtual_write(pin, temperature_Sensor())
    blynk.virtual_write(10, LDR())
    blynk.virtual_write(12, humidity_Sensor())
    blynk.virtual_write(13, start)
    blynk.virtual_write(14, ringing)

###########################################################
# infinite loop that waits for event
###########################################################
#while True:
#    blynk.run()
    
print("-----------------------------------------------------------------")
print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format("RTC Time", "Sys Timer", "Humidity", "Temp","Light","DAC out","Alarm"))
print("-----------------------------------------------------------------")

GPIOsetup()
GPIO.add_event_detect(37, GPIO.FALLING, callback=changeInterval, bouncetime=400)
GPIO.add_event_detect(11, GPIO.FALLING, callback=resetSystemTime, bouncetime=400)
GPIO.add_event_detect(36, GPIO.FALLING, callback=dismissAlarm, bouncetime=400)
GPIO.add_event_detect(7, GPIO.FALLING, callback=monitoring, bouncetime=400)
dataThread = threading.Thread(target = AlertLED)
dataThread.start()

def main():
    
    if start:
            print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format(RTC_time(), str(timer_string()),str(humidity_Sensor())+" V",str(temperature_Sensor())+" C",str(LDR()),str(DAC())+" V",str(fireAlarm())))
            sleep(readingFrequency)
		
		
                #dataThread.start()

if __name__ == "__main__":
	try:
		while True:
                    blynk.run()
                    main()
		    
	except KeyboardInterrupt:
		print("Exiting gracefully")
		spi.close()

	finally:					# run on exit
		spi.close()				# clean up
		
		print("\n All cleaned up")

