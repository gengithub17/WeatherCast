from bs4 import BeautifulSoup
import requests
import json
import datetime
import os
FILEPATH = os.path.dirname(os.path.abspath(__file__))

from PIL import ImageFont, Image, ImageDraw
import epd4in2

class Weather:
	NAGANO = 200000
	json_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{NAGANO}.json"
	wcode_file = f"{FILEPATH}/src/weather_code.json"
	weather_file = f"{FILEPATH}/src/weather.json" #プログラムでは使わないが，一応jsonとして取得しておく
	wcode_json:dict
	weather_data:dict

	reporttime:datetime.datetime
	gettime:datetime.datetime
	
	@classmethod
	def init_class(cls):
		with open(cls.wcode_file,"r",encoding="utf-8") as f:
			cls.wcode_json = json.load(f)
		# data_json = requests.get(cls.json_url).json()
		response = requests.get(cls.json_url)
		data_json = response.json()
		with open(cls.weather_file, "w") as f:
			json.dump(data_json,f, ensure_ascii=False, indent="\t")
		cls.reporttime = datetime.datetime.fromisoformat(data_json[0]["reportDatetime"])
		cls.gettime = datetime.datetime.now()
		cls.weather_data = data_json[0]["timeSeries"][0]
		
	
	def __init__(self, date_index):
		self.date_index = date_index #何日後
		self.date:datetime.date
		self.windex, self.date = self.search_timeDefine() #weather_data内で日付が合致するものを探す
		self.wcode = Weather.weather_data["areas"][0]["weatherCodes"][self.windex]
		self.weather = Weather.wcode_json[self.wcode][3]
		self.img:str = Weather.wcode_json[self.wcode][0]
		self.img =  self.img.replace("svg","png")
	
	def date_comp(self,iso_format): #iso8601形式の日付について，一致するかどうか
		return datetime.datetime.fromisoformat(iso_format).date() == datetime.date.today() + datetime.timedelta(days=self.date_index)

	def search_timeDefine(self):
		for i, timeDefine in enumerate(Weather.weather_data["timeDefines"]):
			if self.date_comp(timeDefine): return i, datetime.datetime.fromisoformat(timeDefine).date()
		raise IndexError

class TempRain: #インスタンスなしクラス #今日と明日の気温，降水データを保持
	url = "https://tenki.jp/forecast/3/23/4810/20201/3hours.html" #3時間ごと
	url2 = "https://tenki.jp/forecast/3/23/4810/20201/" #今日明日の天気
	# forecast/地方(関東甲信越)/(県番号?)/県内地域(北部)/市番号/
	soup:BeautifulSoup
	hours:list[list[str]] #時間リスト #2次元配列(今日と明日)
	rains:list[list[str]] #降水量リスト
	prains:list[list[str]] #降水確率リスト
	temps:list[list[str]] #気温リスト
	highlow:dict #最高最低データ


	@classmethod
	def init(cls): 
		#url
		html = requests.get(cls.url)
		cls.soup = BeautifulSoup(html.content, "html.parser")
		cls.hours = cls.value_get("hour")
		cls.rains = cls.value_get("precipitation")
		cls.prains = cls.value_get("prob-precip", exc="(%)")
		cls.temps = cls.value_get("temperature")
		#url2
		cls.HighLowCalc()
	
	@classmethod
	def value_get(cls,tag:str, exc=None):
		contexts = cls.soup.select(f"[class='{tag}']")
		val_list:list[str] = []
		for con in contexts:
			spans = con.select("span")
			val_list += [span.text for span in spans]
		if exc: #除外対象データ
			val_list = [val for val in val_list if val!=exc]
		#3日間，3時間ごとで計24データあるはず
		if len(val_list)!=24:
			raise ValueError
		#最初の2日間分のみ使用 #クラス変数への格納を考え，2次元配列で返す
		return [[val_list[hour+8*day] for hour in range(8)]for day in range(2)]
	
	@classmethod
	def HighLowCalc(cls): #今日明日について，最高気温，最低気温，またそれぞれの前日との差をdictに集計
		cls.soup = BeautifulSoup(requests.get(cls.url2).content, "html.parser")
		cls.highlow = {
			f"day{day}" : {
				edge : {
					tf : cls.soup.select(f"[class='{edge}-temp temp']")[day].select("[class='value']")[0].text
					if tf == "temp" 
					else cls.soup.select(f"[class='{edge}-temp tempdiff']")[day].text.replace("[","").replace("]","")
					for tf in ["temp","diff"]
				}
				for edge in ["high","low"]
			}
			for day in range(2)
		}
	
	@classmethod
	def HighLowPrint(cls, day:int):
		data = cls.highlow[f"day{day}"]
		return f"{data['high']['temp']}°C / {data['low']['temp']}°C ({int(data['high']['diff']):+}/{int(data['low']['diff']):+})"

class Drawer(ImageDraw.ImageDraw):
	datetime_format = "%m/%d %H:%M"
	date_format = "%m/%d"

	img_dir = f"{FILEPATH}/img/"

	def __init__(self):
		self.epd = epd4in2.EPD()
		self.epd.init()
		
		self.image:Image.Image = Image.new('1',(self.epd.width,self.epd.height),255)
		super().__init__(self.image)
		self.ynow:int = 0
	
	@classmethod
	def font(cls, size):
		return ImageFont.truetype(f"{FILEPATH}/src/Font.ttc",size)
	
	@classmethod
	def back_white(cls, file)->Image.Image:
		img = Image.open(file)
		back = Image.new(img.mode, img.size, (255,255,255))
		back.paste(img, img.split()[-1])
		return back
	
	def drawing(self):
		self.timeStamp(Weather.gettime, Weather.reporttime)
		for weather in WeatherList:
			self.weather(weather)
		self.line((200,self.ynow,200,180))
		self.ynow = 180
		for day in range(2):
			self.rain(day)
		self.display()
	
	def timeStamp(self, get:datetime.datetime, report:datetime.datetime):
		self.text((0,self.ynow), get.strftime(Drawer.datetime_format)+" 取得", font=Drawer.font(15))
		self.text((200,self.ynow), report.strftime(Drawer.datetime_format)+" 発表", font=Drawer.font(15))
		self.ynow += 15
		self.line((0,self.ynow,self.epd.width,self.ynow))
	
	def weather(self, weather:Weather):
		x_edge = weather.date_index*200
		self.text((x_edge,self.ynow), weather.date.strftime(Drawer.date_format), font=Drawer.font(20))
		self.image.paste(Drawer.back_white(Drawer.img_dir+weather.img), (x_edge+50,self.ynow+10))
		self.text((x_edge,self.ynow+120), weather.weather,font=Drawer.font(20))
		self.text((x_edge,self.ynow+140), TempRain.HighLowPrint(weather.date_index), font=Drawer.font(20))
	
	def rain(self, day):
		self.line((0,self.ynow,self.epd.width,self.ynow))
		for i in range(0,self.epd.width,5):
			if i%2:
				self.line((i,self.ynow+20,i+5,self.ynow+20))
		self.text((0,self.ynow), (datetime.date.today()+datetime.timedelta(days=day)).strftime(Drawer.date_format), font=Drawer.font(20))
		self.text((0,self.ynow+20), "降水[mm]", font=Drawer.font(15))
		self.text((0,self.ynow+40), "降水確率", font=Drawer.font(15))
		for i in range(8):
			self.text(((i+2)*40, self.ynow), TempRain.hours[day][i], font=Drawer.font(20))
			self.text(((i+2)*40, self.ynow+20), TempRain.rains[day][i], font=Drawer.font(20))
			self.text(((i+2)*40, self.ynow+40), TempRain.prains[day][i], font=Drawer.font(20))
		self.ynow += 60
	
	def display(self):
		self.epd.display(self.epd.getbuffer(self.image))
		epd4in2.epdconfig.module_exit()

try:
	Weather.init_class()
	WeatherList = [Weather(day) for day in range(2)]
	TempRain.init()
	Drawer().drawing()
	print(Weather.gettime.strftime("%y-%m-%d %H:%M:%S"), os.path.basename(__file__), ": WeatherCast Update.")
except Exception as e:
	print(e)

