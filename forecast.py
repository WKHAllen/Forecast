from weather import Weather
import requests
try:
    from Tkinter import *
    from ttk import *
except ImportError:
    from tkinter import *
    from tkinter.ttk import *
try:
    import cPickle as pickle
except ImportError:
    import pickle
import os
import sys
import time
import StringIO

class WeatherError(Exception):
    pass

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)

def silenceOutput():
    sys.stdout = StringIO.StringIO()

def resetOutput():
    sys.stdout = sys.__stdout__

def c2f(temp):
    return int(round(1.8 * temp + 32))

def f2c(temp):
    return int(round((temp - 32) / 1.8))

def formatTemp(temp, units):
    if units == "F":
        return temp + u"\u00b0" + "F " + str(f2c(int(temp))) + u"\u00b0" + "C"
    elif units == "C":
        return str(c2f(int(temp))) + u"\u00b0" + "F " + temp + u"\u00b0" + "C"
    raise WeatherError("invalid units: " + units)

class App():
    def __init__(self):
        self.running = True
        self.padding = 4
        self.infoPadding = 16
        self.smallFontSize = 10
        self.mediumFontSize = 14
        self.largeFontSize = 24
        self.updateEvery = 60
        self.iconfile = resource_path(os.path.join("data", "icon.ico"))
        self.closeiconfile = resource_path(os.path.join("data", "close.gif"))
        self.savefile = "locations.dat"
        self.locations = []
        self.widgets = []

        self.root = Tk()
        self.root.title("Weather Forecast")
        self.root.iconbitmap(self.iconfile)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.locationSearch = None
        self.notebook = Notebook(self.root)
        self.notebook.enable_traversal()
        self.notebook.pack(padx=self.padding, pady=self.padding, expand=True, fill="both")
        self.root.bind("<Control-w>", lambda e: self.deleteTab())
        self.root.bind("<Control-t>", lambda e: self.notebook.select(len(self.notebook.tabs()) - 1))
        self.addPlusTab()
        self.newTab(self.getLocation(), deletable=False)
        self.loadContent()

        self.root.after(int(1000 * (self.updateEvery - (time.time() % self.updateEvery))), self.updateAll)
        self.root.mainloop()

    def close(self):
        self.running = False
        self.saveContent()
        self.root.destroy()
        sys.exit()

    def getLocation(self):
        url = "http://freegeoip.net/json"
        info = requests.get(url).json()
        location = info["city"] + " " + info["region_name"] + " " + info["country_name"]
        return location

    def getInfo(self, location):
        weather = Weather()
        silenceOutput()
        try:
            lookup = weather.lookup_by_location(location)
        except ValueError:
            raise WeatherError("failed to load data")
        resetOutput()
        if lookup is None:
            raise WeatherError("no such location")

        sunrise = lookup.astronomy()["sunrise"]
        if len(sunrise[sunrise.find(":") + 1:sunrise.find(" ")]) == 1:
            sunrise = sunrise[:sunrise.find(":") + 1] + "0" + sunrise[sunrise.find(":") + 1:]
        sunset = lookup.astronomy()["sunset"]
        if len(sunset[sunset.find(":") + 1:sunset.find(" ")]) == 1:
            sunset = sunset[:sunset.find(":") + 1] + "0" + sunset[sunset.find(":") + 1:]

        windDir = int(lookup.wind()["direction"])
        wind = ""
        if 337.5 <= windDir < 360 or 0 <= windDir < 22.5:
            wind = "N"
        elif 22.5 <= windDir < 67.5:
            wind = "NE"
        elif 67.5 <= windDir < 112.5:
            wind = "E"
        elif 112.5 <= windDir < 157.5:
            wind = "SE"
        elif 157.5 <= windDir < 202.5:
            wind = "S"
        elif 202.5 <= windDir < 247.5:
            wind = "SW"
        elif 247.5 <= windDir < 292.5:
            wind = "W"
        elif 292.5 <= windDir < 337.5:
            wind = "NW"
        wind += " " + lookup.wind()["speed"] + " " + lookup.units()["speed"] + " " + formatTemp(lookup.wind()["chill"], lookup.units()["temperature"])

        forecast = []
        for day in lookup.forecast():
            thisday = {
                "date": day.__dict__["_forecast_data"]["day"] + " " + day.date(),
                "status": day.text(),
                "high": formatTemp(day.high(), lookup.units()["temperature"]),
                "low": formatTemp(day.low(), lookup.units()["temperature"])
            }
            forecast.append(thisday)

        info = {
            "location": ", ".join([i.strip() for i in lookup.location().values()]),
            "city": lookup.location()["city"],
            "time": lookup.last_build_date(),
            "temperature": formatTemp(lookup.condition().temp(), lookup.units()["temperature"]),
            "status": lookup.condition().text(),
            "sunrise": sunrise,
            "sunset": sunset,
            "wind": wind,
            "humidity": lookup.atmosphere()["humidity"] + "%",
            "pressure": lookup.atmosphere()["pressure"] + " " + lookup.units()["pressure"],
            "visibility": lookup.atmosphere()["visibility"] + " " + lookup.units()["distance"],
            "latitude": lookup.latitude(),
            "longitude": lookup.longitude(),
            "forecast": forecast
        }
        return info

    def saveContent(self):
        content = {
            "locations": self.locations,
            "selected": self.notebook.index(self.notebook.select())
        }
        with open(self.savefile, "wb") as f:
            pickle.dump(content, f)

    def loadContent(self):
        try:
            with open(self.savefile, "rb") as f:
                content = pickle.load(f)
            for location in content["locations"]:
                self.newTab(location)
            self.notebook.select(content["selected"])
        except:
            self.notebook.select(0)

    def addPlusTab(self):
        page = Frame(self.notebook)
        newLocation = Label(page, text="Add new location", font=(None, self.smallFontSize))
        newLocation.grid(row=0, column=0, padx=self.padding, pady=self.padding)
        self.locationSearch = Entry(page)
        self.locationSearch.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        self.root.bind("<Return>", lambda e: self.addNewLocation())
        self.root.bind("<Escape>", lambda e: self.locationSearch.delete(0, "end"))
        goButton = Button(page, text="Go", command=self.addNewLocation)
        goButton.grid(row=2, column=0, padx=self.padding, pady=self.padding)
        page.columnconfigure(0, weight=1)
        self.notebook.add(page, text=" + ")

    def deleteTab(self, tab=None):
        if tab is None:
            tab = self.notebook.index(self.notebook.select())
        else:
            tab = self.notebook.index(tab)
        if tab not in (0, len(self.notebook.tabs()) - 1):
            del self.locations[tab - 1]
            del self.widgets[tab]
            self.notebook.forget(tab)

    def addNewLocation(self):
        if self.locationSearch is not None:
            location = self.locationSearch.get().strip()
            self.locationSearch.delete(0, "end")
            if location != "":
                self.newTab(location)
                self.notebook.select(len(self.notebook.tabs()) - 2)

    def newTab(self, location, deletable=True):
        widgets = {}
        if len(self.notebook.tabs()) > 0:
            self.notebook.forget(len(self.notebook.tabs()) - 1)
        page = Frame(self.notebook)
        try:
            info = self.getInfo(location)
        except WeatherError:
            self.locations.append(location)
            tabText = " Error "
            error = Label(page, text="Error loading content", font=(None, self.smallFontSize))
            error.grid(row=0, column=0, padx=self.padding, pady=self.padding)
            widgets["error"] = error
        else:
            if deletable:
                self.locations.append(info["location"])

            tabText = " " + info["city"] + " "
            locationFrame = Frame(page)
            locationFrame.grid(row=0, column=0, sticky="NSEW", pady=self.padding)

            location = Label(locationFrame, text=info["location"], font=(None, self.mediumFontSize))
            location.grid(row=0, column=0, columnspan=4)
            widgets["location"] = location
            status = Label(locationFrame, text=info["status"], font=(None, self.smallFontSize))
            status.grid(row=1, column=0, columnspan=4)
            widgets["status"] = status
            temperature = Label(locationFrame, text=info["temperature"], font=(None, self.largeFontSize))
            temperature.grid(row=2, column=0, columnspan=4)
            widgets["temperature"] = temperature
            time = Label(locationFrame, text=info["time"], font=(None, self.smallFontSize))
            time.grid(row=3, column=0, columnspan=4)
            widgets["time"] = time

            for i in range(locationFrame.grid_size()[0]):
                locationFrame.columnconfigure(i, weight=1)
            for i in range(locationFrame.grid_size()[1]):
                locationFrame.rowconfigure(i, weight=1)

            forecastFrame = Frame(page)
            forecastFrame.grid(row=1, column=0, sticky="NSEW", pady=self.padding)

            dateLabel = Label(forecastFrame, text="Date", font=(None, self.smallFontSize, "bold"))
            dateLabel.grid(row=0, column=0, sticky="W", padx=self.infoPadding)
            statusLabel = Label(forecastFrame, text="Status", font=(None, self.smallFontSize, "bold"))
            statusLabel.grid(row=0, column=1, sticky="W", padx=self.infoPadding)
            highLabel = Label(forecastFrame, text="High", font=(None, self.smallFontSize, "bold"))
            highLabel.grid(row=0, column=2, sticky="W", padx=self.infoPadding)
            lowLabel = Label(forecastFrame, text="Low", font=(None, self.smallFontSize, "bold"))
            lowLabel.grid(row=0, column=3, sticky="W", padx=self.infoPadding)

            forecast = []
            for i in range(len(info["forecast"])):
                day = info["forecast"][i]
                date = Label(forecastFrame, text=day["date"], font=(None, self.smallFontSize))
                date.grid(row=1 + i, column=0, sticky="W", padx=self.infoPadding)
                status = Label(forecastFrame, text=day["status"], font=(None, self.smallFontSize))
                status.grid(row=1 + i, column=1, sticky="W", padx=self.infoPadding)
                high = Label(forecastFrame, text=day["high"], font=(None, self.smallFontSize))
                high.grid(row=1 + i, column=2, sticky="W", padx=self.infoPadding)
                low = Label(forecastFrame, text=day["low"], font=(None, self.smallFontSize))
                low.grid(row=1 + i, column=3, sticky="W", padx=self.infoPadding)
                forecast.append({
                    "date": date,
                    "status": status,
                    "high": high,
                    "low": low
                })
            widgets["forecast"] = forecast

            for i in range(forecastFrame.grid_size()[0]):
                forecastFrame.columnconfigure(i, weight=1)
            for i in range(forecastFrame.grid_size()[1]):
                forecastFrame.rowconfigure(i, weight=1)

            statsFrame = Frame(page)
            statsFrame.grid(row=2, column=0, sticky="NSEW", pady=self.padding)

            sunriseLabel = Label(statsFrame, text="Sunrise", font=(None, self.smallFontSize, "bold"))
            sunriseLabel.grid(row=0, column=0, sticky="W", padx=self.infoPadding)
            sunrise = Label(statsFrame, text=info["sunrise"], font=(None, self.smallFontSize))
            sunrise.grid(row=1, column=0, sticky="W", padx=self.infoPadding)
            widgets["sunrise"] = sunrise
            sunsetLabel = Label(statsFrame, text="Sunset", font=(None, self.smallFontSize, "bold"))
            sunsetLabel.grid(row=0, column=1, sticky="W", padx=self.infoPadding)
            sunset = Label(statsFrame, text=info["sunset"], font=(None, self.smallFontSize))
            sunset.grid(row=1, column=1, sticky="W", padx=self.infoPadding)
            widgets["sunset"] = sunset
            windLabel = Label(statsFrame, text="Wind", font=(None, self.smallFontSize, "bold"))
            windLabel.grid(row=0, column=2, sticky="W", padx=self.infoPadding)
            wind = Label(statsFrame, text=info["wind"], font=(None, self.smallFontSize))
            wind.grid(row=1, column=2, sticky="W", padx=self.infoPadding)
            widgets["wind"] = wind
            humidityLabel = Label(statsFrame, text="Humidity", font=(None, self.smallFontSize, "bold"))
            humidityLabel.grid(row=0, column=3, sticky="W", padx=self.infoPadding)
            humidity = Label(statsFrame, text=info["humidity"], font=(None, self.smallFontSize))
            humidity.grid(row=1, column=3, sticky="W", padx=self.infoPadding)
            widgets["humidity"] = humidity

            pressureLabel = Label(statsFrame, text="Pressure", font=(None, self.smallFontSize, "bold"))
            pressureLabel.grid(row=2, column=0, sticky="W", padx=self.infoPadding)
            pressure = Label(statsFrame, text=info["pressure"], font=(None, self.smallFontSize))
            pressure.grid(row=3, column=0, sticky="W", padx=self.infoPadding)
            widgets["pressure"] = pressure
            visibilityLabel = Label(statsFrame, text="Visibility", font=(None, self.smallFontSize, "bold"))
            visibilityLabel.grid(row=2, column=1, sticky="W", padx=self.infoPadding)
            visibility = Label(statsFrame, text=info["visibility"], font=(None, self.smallFontSize))
            visibility.grid(row=3, column=1, sticky="W", padx=self.infoPadding)
            widgets["visibility"] = visibility
            latitudeLabel = Label(statsFrame, text="Latitude", font=(None, self.smallFontSize, "bold"))
            latitudeLabel.grid(row=2, column=2, sticky="W", padx=self.infoPadding)
            latitude = Label(statsFrame, text=info["latitude"], font=(None, self.smallFontSize))
            latitude.grid(row=3, column=2, sticky="W", padx=self.infoPadding)
            widgets["latitude"] = latitude
            longitudeLabel = Label(statsFrame, text="Longitude", font=(None, self.smallFontSize, "bold"))
            longitudeLabel.grid(row=2, column=3, sticky="W", padx=self.infoPadding)
            longitude = Label(statsFrame, text=info["longitude"], font=(None, self.smallFontSize))
            longitude.grid(row=3, column=3, sticky="W", padx=self.infoPadding)
            widgets["longitude"] = longitude

            for i in range(statsFrame.grid_size()[0]):
                statsFrame.columnconfigure(i, weight=1)
            for i in range(statsFrame.grid_size()[1]):
                statsFrame.rowconfigure(i, weight=1)

        if deletable:
            closeImage = PhotoImage(file=self.closeiconfile)
            closeButton = Button(page, image=closeImage)
            closeButton.config(command=lambda p=page: self.deleteTab(p))
            closeButton.grid(row=0, column=0, sticky="NE")
            closeButton.image = closeImage

        for i in range(page.grid_size()[0]):
            page.columnconfigure(i, weight=1)
        for i in range(page.grid_size()[1]):
            page.rowconfigure(i, weight=1)
        
        self.widgets.append(widgets)
        self.notebook.add(page, text=tabText)
        self.addPlusTab()

    def updateInfo(self, tab, location):
        try:
            info = self.getInfo(location)
        except WeatherError:
            tabText = " Error "
        else:
            tabText = " " + info["city"] + " "
            for key in self.widgets[tab].keys():
                if key != "forecast":
                    self.widgets[tab][key].config(text=info[key])
            for i in range(len(self.widgets[tab]["forecast"])):
                for item in self.widgets[tab]["forecast"][i].keys():
                    self.widgets[tab]["forecast"][i][item].config(text=info["forecast"][i][item])
        self.notebook.tab(tab, text=tabText)

    def updateAll(self):
        if not self.running:
            return
        self.saveContent()
        self.updateInfo(0, self.getLocation())
        for i in range(1, len(self.widgets)):
            self.updateInfo(i, self.locations[i - 1])
        self.root.after(int(1000 * (self.updateEvery - (time.time() % self.updateEvery))), self.updateAll)

if __name__ == "__main__":
    App()
