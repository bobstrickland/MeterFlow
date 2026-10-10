import random
import sys
from datetime import datetime , timedelta, timezone
from collections import deque

randomSeed:int = 233
fileName:str = "output.csv"

class meter:
    def __init__(self, id:int, currentTime:datetime):
        self.id = id
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
            self.currentTime = self.currentTime.replace(minute = minutes, second = 0, microsecond = 0)
        else:
            self.currentTime = self.currentTime.replace(second = 0, microsecond = 0)

    def getReading(self, currentTime:datetime) -> float:
        currentTime = currentTime.replace(second=0, microsecond=0)
        while (currentTime >= self.currentTime+timedelta(minutes=15)):
            self.reading = self.reading + random.uniform(0,30)
            if (self.currentTime.hour in (16, 17, 18, 19, 20)):
                self.reading = self.reading + random.uniform(0,30)
            if (self.currentTime.hour in (17, 18)):
                self.reading = self.reading + random.uniform(0,30)
            self.currentTime = self.currentTime+timedelta(minutes=15)
        return self.reading;

    def printMeter(self, requestTime:datetime, gatewayId:str, gatewaySequence:int) -> str:
        merterId:str = f"M{self.id:04d}"
        timestamp:str = (self.currentTime-timedelta(minutes=15)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        requestTimestamp:str = requestTime.isoformat(timespec='seconds').replace('+00:00', 'Z')
        readingId:str = f"{merterId}|{timestamp}|kWh"
        qualityFlag:str="OK"
        schemaVersion:int=1
        return f"{readingId},{merterId},{timestamp},{self.reading:.3f},ACTUAL,{requestTimestamp},{gatewayId},{gatewaySequence},{qualityFlag},{schemaVersion}"

class Gateway:
    def __init__(self, id:str):
        self.id = id
        self.sequence:int = 0
    def getSequence(self) -> int:
        rv:int = self.sequence
        self.sequence += 1
        return rv
    def getId(self) -> str:
        return self.id        

def generateReadingsForGivenTime(currentDatetime:datetime, meterList: list[meter]):
    for themeter in meterList:
        themeter.getReading(currentDatetime)

def printHeaders():
    with open(fileName, "w", encoding="utf-8") as f:
        f.write("reading_id,meter_id,interval_start,register_kwh,read_type,received_at,gateway_id,gateway_seq,quality_flag,schema_version")

def appendLine(line:str):
    with open(fileName, "a", encoding="utf-8") as f:
        f.write(line)

def sampleForDupeStack(line:str, dupeStack: deque[str]):
    if (random.randint(0,1000) < 2):
        dupeStack.append(line)
    if (dupeStack and random.randint(0,300) == 0):
        appendLine(dupeStack.pop())

def printMeters(requestTime:datetime, gateway:Gateway, meterList: list[meter], dupeStack: deque[str]):
    with open(fileName, "a", encoding="utf-8") as f:
        for m in meterList:
            line:str = f"\n{m.printMeter(requestTime, gateway.getId(), gateway.getSequence())}"
            f.write(line)
            sampleForDupeStack(line, dupeStack)

def generateReadings():
    random.seed(randomSeed)
    meterList: list[meter] = list()
    dupeStack: deque[str] = deque()
    currentDatetime:datetime = datetime.now(tz=timezone.utc).replace(hour=0, minute=15, second=0, microsecond=0)
    gateway:Gateway = Gateway("G001")
    printHeaders()
    print(currentDatetime)
    for i in range(50):
        newMeter:meter = meter(i, currentDatetime)
        meterList.append(newMeter)
    for i in range(192):
        generateReadingsForGivenTime(currentDatetime, meterList)
        printMeters(currentDatetime, gateway, meterList, dupeStack)
        currentDatetime = currentDatetime+timedelta(minutes=15)

if __name__ == "__main__":
    sys.exit(generateReadings())