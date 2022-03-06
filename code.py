import analogio
import board
import displayio
import rtc
import terminalio
import time

from adafruit_display_text import label
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_progressbar.horizontalprogressbar import (HorizontalProgressBar, HorizontalFillDirection)
from adafruit_ssd1351 import SSD1351

clock = rtc.RTC()
clock.datetime = time.struct_time((2022, 3, 6, 4, 0, 0, 0, -1, -1))

displayio.release_displays()

spi = board.SPI()
oled_dc = board.D24
oled_cs = board.D25

display_bus = displayio.FourWire(spi, command=oled_dc, chip_select=oled_cs, reset=board.D9, baudrate=18000000)
display = SSD1351(display_bus, width=128, height=128)

battery = analogio.AnalogIn(board.A1)

dst_start = (3,2,6,2)
dst_end = (11,1,6,2)
dst_offset = 3600

timezone_desc = ("EST", "EDT")
timezone_offset = -5

day_text = ("MON","TUE","WED","THU","FRI","SAT","SUN")
month_text = ("","JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC")

grid_upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
grid_lower = 'abcdefghijklmnopqrstuvwx'

battery_level = (0, 6553, 13107, 19660, 26214, 32768, 39321, 45875, 52428, 58982, 65535)

battery_gradient = [(0.0, 0xFF0000), (0.30, 0xFF7F00), (0.50, 0xFFFF00), (0.70, 0x00FF00)]
battery_palette = fancy.expand_gradient(battery_gradient, 100)
battery_colors = []

for i in range(100):
  color = fancy.palette_lookup(battery_palette, i / 100)
  battery_colors.append(color.pack())
  
bitmap = displayio.OnDiskBitmap("/images/ab9xa.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
display_group = displayio.Group()
display_group.append(tile_grid)
display.show(display_group)
time.sleep(1.0)
display_group.remove(tile_grid)

clock_color = 0x0000FF
date_color = 0x00FF00
location_color = 0x0000FF

font = terminalio.FONT

startup_text_gps = "Waiting for GPS Fix"
startup_text = label.Label(font, text=startup_text_gps, color=0xFFFFFF, x=0, y=64)
display_group.append(startup_text)
time.sleep(1.0)
display_group.remove(startup_text)
  
battery_progress_bar = HorizontalProgressBar((112, 0), (16, 8), value=0, min_value=0, max_value=100, fill_color=0x000000, outline_color=0xFFFFFF, bar_color=0x00FF00, direction=HorizontalFillDirection.LEFT_TO_RIGHT)
display_group.append(battery_progress_bar)

default_utc_clock_text = "00:00:00 UTC"
default_tz_clock_text = "00:00:00 " + timezone_desc[0]
default_utc_date_text = "SUN JAN 01, 2020"
default_tz_date_text = "SUN JAN 01, 2020"

utc_clock_text = label.Label(font, text=default_utc_clock_text, color=clock_color, x=0, y=3)
utc_date_text = label.Label(font, text=default_utc_date_text, color=date_color, x=0, y=14)
tz_clock_text = label.Label(font, text=default_tz_clock_text, color=clock_color, x=0, y=30)
tz_date_text = label.Label(font, text=default_tz_date_text, color=date_color, x=0, y=41)

display_group.append(utc_clock_text)
display_group.append(utc_date_text)
display_group.append(tz_clock_text)
display_group.append(tz_date_text)

default_lat_text = "Lat:  00.0000" + chr(176) + " N"
default_lon_text = "Lon: 000.0000° W"

lat_text = label.Label(font, text=default_lat_text, color=location_color, x=0, y=57)
lon_text = label.Label(font, text=default_lon_text, color=location_color, x=0, y=68)

display_group.append(lat_text)
display_group.append(lon_text)

default_grid_text = "Grid: AA00jj"

grid_text = label.Label(font, text=default_grid_text, color=location_color, x=0, y=84)

display_group.append(grid_text)

time.sleep(1.0)

class calc_datetime:
  def __init__(self, base_time_secs):
    time_utc_tuple=time.localtime(base_time_secs)

    base_year = time_utc_tuple[0]
    error_check_tuple = (base_year, 1, 1, 0, 0, 0, 0, 0, 0)
    error_check_secs = time.mktime(error_check_tuple) - timezone_offset * 86400

    if base_time_secs < error_check_secs:
      base_year -= 1

    dst_start_tuple = (base_year, dst_start[0], dst_start[1] * 7 - 6, dst_start[3], 0, 0, 0, 0, 0)
    dst_start_secs = time.mktime(dst_start_tuple)
    dst_start_tuple = time.localtime(dst_start_secs)

    dst_start_diff = dst_start[2] - dst_start_tuple[6]

    if dst_start_diff < 0:
      dst_start_diff += 7

    dst_start_secs += dst_start_diff * 86400

    dst_end_tuple = (base_year, dst_end[0], dst_end[1] * 7 - 6, dst_end[3], 0, 0, 0, 0, 0)
    dst_end_secs = time.mktime(dst_end_tuple) - dst_offset
    dst_end_tuple = time.localtime(dst_end_secs)

    dst_end_diff = dst_end[2] - dst_end_tuple[6]

    if dst_end_diff < 0:
      dst_end_diff += 7

    dst_end_secs += dst_end_diff * 86400

    if base_time_secs >= dst_start_secs and base_time_secs < dst_end_secs:
      dst_active = True
    else:
      dst_active = False

    self.utc_date = "{} {} {:02d}, {}".format(day_text[time_utc_tuple[6]],month_text[time_utc_tuple[1]],time_utc_tuple[2],time_utc_tuple[0])
    self.utc_time = "{:02d}:{:02d}:{:02d} UTC".format(time_utc_tuple[3],time_utc_tuple[4],time_utc_tuple[5])

    time_tz_secs = base_time_secs + timezone_offset * 3600 + dst_active * dst_offset
    time_tz_tuple = time.localtime(time_tz_secs)

    self.tz_date = "{} {} {:02d}, {}".format(day_text[time_tz_tuple[6]],month_text[time_tz_tuple[1]],time_tz_tuple[2],time_tz_tuple[0])
    self.tz_time = "{:02d}:{:02d}:{:02d} {}".format(time_tz_tuple[3],time_tz_tuple[4],time_tz_tuple[5],timezone_desc[dst_active])

def calc_position (latitude, longitude):
  grid_lat_adj = latitude + 90
  grid_lat_sq = grid_upper[int(grid_lat_adj / 10)]
  grid_lat_field = str(int(grid_lat_adj%10))
  grid_lat_rem = (grid_lat_adj - int(grid_lat_adj)) * 60
  grid_lat_subsq = grid_lower[int(grid_lat_rem / 2.5)]

  grid_lon_adj = longitude + 180
  grid_lon_sq = grid_upper[int(grid_lon_adj / 20)]
  grid_lon_field = str(int((grid_lon_adj/2)%10))
  grid_lon_rem = (grid_lon_adj - int(grid_lon_adj / 2) * 2) * 60
  grid_lon_subsq = grid_lower[int(grid_lon_rem / 5)]

  return grid_lon_sq + grid_lat_sq + grid_lon_field + grid_lat_field + grid_lon_subsq + grid_lat_subsq

def main():
  last_utc_time = ""
  last_utc_date = ""
  last_tz_time = ""
  last_tz_date = ""
  last_grid_sq = ""
  last_battery = 0
  last_battery_percent = 0

  while True:
    current_datetime = calc_datetime(time.time())

    if last_utc_time != current_datetime.utc_time:
      utc_clock_text.text = current_datetime.utc_time
      last_utc_time = current_datetime.utc_time

    if last_utc_date != current_datetime.utc_date:
      utc_date_text.text = current_datetime.utc_date
      last_utc_date = current_datetime.utc_date

    if last_tz_time != current_datetime.tz_time:
      tz_clock_text.text = current_datetime.tz_time
      last_tz_time = current_datetime.tz_time

    if last_tz_date != current_datetime.tz_date:
      tz_date_text.text = current_datetime.tz_date
      last_tz_date = current_datetime.tz_date

    current_grid_sq = calc_position(35.5844,-78.5171)
    lat_text.text = "Lat:  35.5844"
    lon_text.text = "Lon: -78.5171"
    
    if last_grid_sq != current_grid_sq:
      grid_text.text = "Grid: " + current_grid_sq
      last_grid_sq = current_grid_sq

    current_battery = battery.value
    current_battery_percent = 0
    
    for percent in range(10, 1, -1):
      if current_battery <= battery_level[percent] and current_battery > battery_level[percent - 1]:
        current_battery_percent = percent * 10
        break

    if last_battery_percent != current_battery_percent:
      battery_progress_bar.bar_color = battery_colors[current_battery_percent - 1]
      battery_progress_bar.value = current_battery_percent
      last_battery_percent = current_battery_percent

    time.sleep(0.5)

main()
