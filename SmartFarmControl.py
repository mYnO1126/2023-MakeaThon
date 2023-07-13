import RPi.GPIO as GPIO
import time
from enum import Enum
import numpy as np
import signal                   
import sys

MOTOR_X_CW_PIN=13
MOTOR_X_CLK_PIN=6
MOTOR_Y_CW_PIN=26
MOTOR_Y_CLK_PIN=19
MOTOR_Z_CW_PIN=21
MOTOR_Z_CLK_PIN=20

END_SWITCH_X1=22
END_SWITCH_X2=23
END_SWITCH_Y1=24
END_SWITCH_Y2=25
END_SWITCH_Z1=27
END_SWITCH_Z2=17

X_LEN=27217
Y_LEN=19052
Z_LEN=26757

X_UNIT=1000
Z_UNIT=1000

X_OFFSET=100
Z_OFFSET=100

Y_IN_DIST=1000
Z_UP_DIST=1000

OUT=GPIO.OUT
IN=GPIO.IN

ROTATION_T=0.001
STOP_T=0.001

class Motor(Enum):
    X = 0
    Y = 1
    Z = 2
class Dir(Enum):
    CW = True #GPIO.HIGH
    CCW = False #GPIO.LOW

class SmartFarmControl():
    def __init__(self):
        self.xpos=0
        self.ypos=0
        self.zpos=0

        self.xlen=0
        self.ylen=0
        self.zlen=0
        self.counter=0
        self.xcounter=0
        self.ycounter=0
        self.zcounter=0

        self.emergencyStop=False
        
        self.modes=["initialization" for i in range(3)]
        self.setPinMode()

        
        # self.initializing_end_to_end()

        """
        An initialization function

        Parameters
        ----------
        origin: origin of passenger

        dest: destination of passenger

        state: one of WAIT, ONBOARD, ARRIVAL
            
        """
    def setPinMode(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_X_CW_PIN,OUT)
        # GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_X_CLK_PIN,OUT)

        # GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_Y_CW_PIN,OUT)
        # GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_Y_CLK_PIN,OUT)

        # GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_Z_CW_PIN,OUT)
        # GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOTOR_Z_CLK_PIN,OUT)

        GPIO.setup(END_SWITCH_X1, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(END_SWITCH_X2, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.add_event_detect(END_SWITCH_X1, GPIO.FALLING, callback=self.switchX1Pressed,bouncetime=300)
        GPIO.add_event_detect(END_SWITCH_X2, GPIO.FALLING, callback=self.switchX2Pressed,bouncetime=300)

        GPIO.setup(END_SWITCH_Y1, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(END_SWITCH_Y2, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.add_event_detect(END_SWITCH_Y1, GPIO.FALLING, callback=self.switchY1Pressed,bouncetime=300)
        GPIO.add_event_detect(END_SWITCH_Y2, GPIO.FALLING, callback=self.switchY2Pressed,bouncetime=300)

        GPIO.setup(END_SWITCH_Z1, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(END_SWITCH_Z2, IN, pull_up_down = GPIO.PUD_UP)
        GPIO.add_event_detect(END_SWITCH_Z1, GPIO.FALLING, callback=self.switchZ1Pressed,bouncetime=300)
        GPIO.add_event_detect(END_SWITCH_Z2, GPIO.FALLING, callback=self.switchZ2Pressed,bouncetime=300)

    def checkMode(self):
        for mode in self.modes:
            if mode=="initialization":
                return False
        return True
    def checkMotorMode(self,motor):
        if motor==Motor.X:motor=0
        if motor==Motor.Y:motor=1       
        if motor==Motor.Z:motor=2
        if self.modes[motor]=="initialization":
            return False
        else:
            return True

    def setMotorRotationDir(self,motor,dir):
        if motor==Motor.X:
            GPIO.output(MOTOR_X_CW_PIN,dir)
        elif motor==Motor.Y:
            GPIO.output(MOTOR_Y_CW_PIN,not dir)
        elif motor==Motor.Z:
            GPIO.output(MOTOR_Z_CW_PIN,not dir)

    def setMotorsRotationDir(self,motors,dir):
        for motor in motors:
            self.setMotorRotationDir(motor,dir)

    def moveMotors(self,motors):
        for motor in motors:
            if motor==Motor.X:
                GPIO.output(MOTOR_X_CLK_PIN,True)
            elif motor==Motor.Y:
                GPIO.output(MOTOR_Y_CLK_PIN,True)
            elif motor==Motor.Z:
                GPIO.output(MOTOR_Z_CLK_PIN,True)
        time.sleep(ROTATION_T)
        for motor in motors:
            if motor==Motor.X:
                GPIO.output(MOTOR_X_CLK_PIN,False)
            elif motor==Motor.Y:
                GPIO.output(MOTOR_Y_CLK_PIN,False)
            elif motor==Motor.Z:
                GPIO.output(MOTOR_Z_CLK_PIN,False)
        time.sleep(STOP_T)
    
    def movableMotors(self,distances):
        motors=[]
        if distances[0]!=0:
            motors.append(Motor.X)
        if distances[1]!=0:
            motors.append(Motor.Y)
        if distances[2]!=0:
            motors.append(Motor.Z)

    def updateDistance(self,distances):
        updatedDistance=[]
        for distance in distances:
            if distance>0:
                updatedDistance.append(distance-1)
            elif distance<0:
                updatedDistance.append(distance+1)
            elif distance==0:
                updatedDistance.append(0)
        return updatedDistance

    def moveMotorsDistance(self,distances):
        distances=int(distances)
        if distances[0]>=0:
            if distances[0]+self.xpos>=self.xlen:
                distances[0]=self.xlen-self.xpos-1
        else:
            if distances[0]+self.xpos<=0:
                distances[0]=-self.xpos+1
        if distances[1]>=0:
            if distances[1]+self.ypos>=self.ylen:
                distances[1]=self.ylen-self.ypos-1
        else:
            if distances[1]+self.ypos<=0:
                distances[1]=-self.ypos+1
        if distances[2]>=0:
            if distances[2]+self.zpos>=self.zlen:
                distances[2]=self.zlen-self.zpos-1
        else:
            if distances[2]+self.zpos<=0:
                distances[2]=-self.zpos+1
        maxdist=max(abs(distances))
        for i in range(maxdist):
            self.moveMotors(self.movableMotors(distances))
            distances=self.updateDistance(distances)

    def moveMotorsToCoords(self,coords):
        x=coords[0]
        z=coords[1]

        distances=((x*X_UNIT+X_OFFSET)*self.xlen-self.xpos,0,(z*Z_UNIT+Z_OFFSET)*self.zlen-self.zpos)

        self.moveMotorsDistance(distances)

    def moveMotorsToOrigin(self):
        distances=(1000-self.xpos,1000-self.ypos,1000-self.zpos)
        self.moveMotorsDistance(distances)

    def moveMotorsOrigDest(self,orig,dest):
        self.moveMotorsToCoords(orig)
        time.sleep(0.1)
        self.moveMotorsDistance([0,Y_IN_DIST,0])#Y IN
        time.sleep(0.1)
        self.moveMotorsDistance([0,0,Z_UP_DIST])#Z UP
        time.sleep(0.1)
        self.moveMotorsDistance([0,-Y_IN_DIST,0])#Y IN   
        time.sleep(0.1)      #catch

        self.moveMotorsToCoords(dest)
        self.moveMotorsDistance([0,0,Z_UP_DIST])#Z UP
        time.sleep(0.1)
        self.moveMotorsDistance([0,Y_IN_DIST,0])#Y IN
        time.sleep(0.1)
        self.moveMotorsDistance([0,0,-Z_UP_DIST])#Z UP
        self.moveMotorsDistance([0,-Y_IN_DIST,0])#Y IN

    def test(self):
        self.setMotorsRotationDir([Motor.Y],True)
        counter=0
        self.counter=0
        while True:
            self.moveMotors([Motor.Y])
            self.counter+=1
            print(self.counter)
            # if self.emergencyStop==True:
            #     counter+=1
            #     if counter==100:break
            if self.counter==1000:
                break


            ## y,z reverse


    def initializing_end_to_end(self):
        self.setMotorsRotationDir([Motor.X,Motor.Y,Motor.Z],True)
        self.counter=0
        while True:
            self.moveMotors([Motor.X,Motor.Y,Motor.Z])
            self.counter+=1
            print(self.counter)
            if self.checkMode():
                break
        self.counter=0
        while True:
            self.moveMotors([Motor.X])
            self.counter+=1
            print(self.counter)
            if self.counter==1000:
                break
        
    def initializing_origin(self):
        motors=[Motor.X,Motor.Y,Motor.Z]
        self.setMotorsRotationDir(motors,False)
        self.counter=np.zeros(3)
        while True:
            self.moveMotors(motors)
            self.counter+=1
            if self.checkMode():
                break
            # for motor in motors:
            #     if self.checkMotorMode(motor):
            #         motors.remove(motor)
        self.moveMotorsToOrigin()

        
    def switchX1Pressed(self,channel):
        if self.modes[0]=="initialization":
            print("x1")
            self.xpos=0
            self.xlen=self.counter-self.xlen
            print("xlen: "+str(self.xlen))
            self.modes[0]="normal"
            self.setMotorRotationDir(Motor.X,True)
        else:
            self.xpos=0
            self.setMotorRotationDir(Motor.X,True)
    def switchX2Pressed(self,channel):
        if self.modes[0]=="initialization":
            print("x2")
            self.xlen=self.counter
            self.setMotorRotationDir(Motor.X,False)
        else:
            self.xpos=self.xlen
            self.setMotorRotationDir(Motor.X,False)
    def switchY1Pressed(self,channel):
        if self.modes[1]=="initialization":
            print("y1")
            self.ypos=0
            self.ylen=self.counter-self.ylen
            print("ylen: "+str(self.ylen))
            self.modes[1]="normal"
            self.setMotorRotationDir(Motor.Y,True)
        else:
            self.ypos=0
            self.setMotorRotationDir(Motor.Y,True)
    def switchY2Pressed(self,channel):
        if self.modes[1]=="initialization":
            print("y2")
            self.ylen=self.counter
            self.setMotorRotationDir(Motor.Y,False)
            self.emergencyStop=True
        else:
            self.ypos=self.ylen
            self.setMotorRotationDir(Motor.Y,False)
    def switchZ1Pressed(self,channel):
        if self.modes[2]=="initialization":
            print("z1")
            self.zpos=0
            self.zlen=self.counter-self.zlen
            print("zlen: "+str(self.zlen))
            self.modes[2]="normal"
            self.setMotorRotationDir(Motor.Z,True)
        else:
            self.zpos=0
            self.setMotorRotationDir(Motor.Z,True)
    def switchZ2Pressed(self,channel):
        if self.modes[2]=="initialization":
            print("z2")
            self.zlen=self.counter
            self.setMotorRotationDir(Motor.Z,False)
        else:
            self.zpos=self.zlen
            self.setMotorRotationDir(Motor.Z,False)

    


