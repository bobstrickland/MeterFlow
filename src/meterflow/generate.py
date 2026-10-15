import random
import sys
from datetime import datetime , timedelta, timezone
from collections import deque

randomSeed:int = 233

class Gateway:
    readings_per_gateway:int = 1000
    def __init__(self, id:str):
        self.id = id
        self.sequence:int = 0
    def getSequence(self) -> int:
        rv:int = self.sequence
        self.sequence += 1
        return rv
    def getId(self) -> str:
        return self.id        

class meter:
    def __init__(self, id:int, gateway:Gateway, currentTime:datetime):
        self.id = id
        self.gateway = gateway
        self.reading = random.uniform(5000, 100000)
        self.currentTime = currentTime
        if (self.currentTime.minute not in (0,15,30,45)) :
            minutes:int = self.currentTime.minute
            match minutes:
                case minutes if minutes < 8:
                    minutes = 0
                case minutes if minutes < 23:
                    minutes = 15
                case minutes if minutes < 38:
                    minutes = 30
                case _:
                    minutes = 45
            self.currentTime = self.currentTime.replace(minute = minutes, second = 0, microsecond = 0) - timedelta(minutes=15)
        else:
            self.currentTime = self.currentTime.replace(second = 0, microsecond = 0) - timedelta(minutes=15)

    def getReading(self, currentTime:datetime) -> float:
        currentTime = currentTime.replace(second=0, microsecond=0)
        while currentTime >= self.currentTime+timedelta(minutes=15):
            self.reading = self.reading + random.uniform(0,.4)
            if (self.currentTime.hour in (16, 17, 18, 19, 20)):
                self.reading = self.reading + random.uniform(0,.45)
            if (self.currentTime.hour in (17, 18)):
                self.reading = self.reading + random.uniform(0,.35)
            self.currentTime = self.currentTime+timedelta(minutes=15)
        return self.reading;

    def printMeter(self, requestTime:datetime) -> str:
        gatewayId:str = self.gateway.getId()
        gatewaySequence:int = self.gateway.getSequence()
        merterId:str = f"M{self.id:04d}"
        timestamp:str = (self.currentTime-timedelta(minutes=15)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        
        
        requestTimestamp:str = (requestTime+timedelta(minutes=random.randint(0, 9))).replace(second=random.randint(0, 59)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        readingId:str = f"{merterId}|{timestamp}|kWh"
        qualityFlag:str="OK"
        schemaVersion:int=1
        return f"{readingId},{merterId},{timestamp},{self.reading:.3f},ACTUAL,{requestTimestamp},{gatewayId},{gatewaySequence},{qualityFlag},{schemaVersion}"


def generateReadingsForGivenTime(currentDatetime:datetime, meterList: list[meter]):
    for themeter in meterList:
        themeter.getReading(currentDatetime)

def printHeaders(fileName:str):
    with open(fileName, "w", encoding="utf-8") as f:
        f.write("reading_id,meter_id,interval_start,register_kwh,read_type,received_at,gateway_id,gateway_seq,quality_flag,schema_version")

def appendLine(line:str, fileName:str):
    with open(fileName, "a", encoding="utf-8") as f:
        f.write(line)

def sampleForDupeStack(line:str, dupeStack: deque[str], fileName:str):
    if random.random() < 0.003:
        dupeStack.append(line)
    if (dupeStack and random.randint(0,300) == 0):
        appendLine(dupeStack.pop(), fileName)

def printMeters(requestTime:datetime, meterList: list[meter], dupeStack: deque[str], fileName:str):
    with open(fileName, "a", encoding="utf-8") as f:
        for m in meterList:
            line:str = f"\n{m.printMeter(requestTime)}"
            if random.random() > 0.001: #99.9% chance of writing the line. 0.05% chance of losing it, and 0.05% chance of wirting it later on.
                f.write(line)
            elif random.getrandbits(1):
                dupeStack.append(line)
            sampleForDupeStack(line, dupeStack, fileName)

def generateReadings(number_of_meters:int,dupeStack: deque[str], fileName:str, currentDatetime:datetime, gateway_array: list[Gateway]):
    meterList: list[meter] = list()
    #dupeStack: deque[str] = deque()
    printHeaders(fileName)
    print(currentDatetime)
    for i in range(number_of_meters):
        newMeter:meter = meter(i, gateway_array[i//Gateway.readings_per_gateway], currentDatetime)
        meterList.append(newMeter)
    for i in range(96):
        generateReadingsForGivenTime(currentDatetime, meterList)
        printMeters(currentDatetime, meterList, dupeStack, fileName)
        currentDatetime = currentDatetime+timedelta(minutes=15)

if __name__ == "__main__":
    random.seed(randomSeed)
    number_of_meters:int = 10000
    dupeStack: deque[str] = deque()
    
    gateway_array: list[Gateway] = []
    for i in range(number_of_meters//Gateway.readings_per_gateway):
        gateway_array.append(Gateway(f"G{i:03d}"))
    
    currentDatetime:datetime = datetime.strptime("2026-10-01", "%Y-%m-%d").replace(tzinfo=timezone.utc,hour=0, minute=15, second=0, microsecond=0) 
    
    for i in range(21) :
        generateReadings(number_of_meters, dupeStack, f"output{i:02d}.csv", currentDatetime + timedelta(days=i), gateway_array)
    
    sys.exit()
