import analogio
import board
import busio
import displayio
import math
import rtc
import terminalio
import time

import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_gps
import adafruit_lsm303dlh_mag

from adafruit_display_text import label
from adafruit_progressbar.horizontalprogressbar import (HorizontalProgressBar, HorizontalFillDirection)
from adafruit_ssd1351 import SSD1351

# SETUP CLOCK
clock = rtc.RTC()

# SETUP OLED DISPLAY
displayio.release_displays()
spi = board.SPI()
display_bus = displayio.FourWire(spi, command=board.D24, chip_select=board.D25, reset=board.D4, baudrate=18000000)
display = SSD1351(display_bus, width=128, height=128)

# SETUP MAGNETOMETER
i2c = board.I2C()
compass = adafruit_lsm303dlh_mag.LSM303DLH_Mag(i2c)

# SETUP ADC FOR BATTERY MONITORING
battery = analogio.AnalogIn(board.A1)

# DISPLAY SPLASH LOGO
bitmap = displayio.OnDiskBitmap('/images/ab9xa.bmp')
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
display_group = displayio.Group()
display_group.append(tile_grid)
display.show(display_group)

# DST START / END (MONTH, WEEK, DAY, HOUR)
dst_start = (3,2,6,2)
dst_end = (11,1,6,2)
dst_offset = 3600

# TIMEZONE DATA
timezone_desc = ('EST', 'EDT')
timezone_offset = -5

# ARRAYS FOR DATE, MONTH TEXT
day_text = ('MON','TUE','WED','THU','FRI','SAT','SUN')
month_text = ('','JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')

# COMPASS DATA
compass_angle = (11.25, 33.75, 56.25, 78.75, 101.25, 123.75, 146.25, 168.75, 191.25, 213.75, 236.25, 258.75, 281.25, 303.75, 326.25, 348.75)
compass_point = ('NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')

# ARRAYS FOR GRID SQUARE TEXT
grid_upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
grid_lower = 'abcdefghijklmnopqrstuvwx'

# TO DO: CALCULATE BATTERY PERCENTAGE MAP AND UPDATE VALUES
# ================================================================
battery_list_elements = 10

# ARRAY FOR ADC VALUE TO BATTERY PERCENTAGE (0%, 10%, 20%...)
battery_level = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# CREATE COLOR GRADIENT AND PALETTE FOR BATTERY GAUGE
battery_gradient = [(0.0, 0xFF0000), (0.25, 0xFF7F00), (0.50, 0xFFFF00), (0.75, 0x00FF00)]
battery_palette = fancy.expand_gradient(battery_gradient, 100)
battery_colors = []

for i in range(100):
  color = fancy.palette_lookup(battery_palette, i / 100)
  battery_colors.append(color.pack())

# REMOVE SPLASH LOGO
time.sleep(2.0)
display_group.remove(tile_grid)

# TEXT COLOR SETUP
clock_color = 0x00FF00
date_color = 0x0000FF
location_color = 0x00FF00
grid_color = 0xFFFF00
sat_color = 0xFF00FF

font = terminalio.FONT

# WAIT FOR INITIAL GPS FIX
startup_text_gps = 'Waiting For GPS Fix'
startup_text = label.Label(font, text=startup_text_gps, color=0xFFFFFF, x=8, y=64)
display_group.append(startup_text)

counter_gps = 0
counter_text = label.Label(font, text='{:04d}'.format(counter_gps), color=0xFFFFFF, x=105, y=123)
display_group.append(counter_text)

# SETUP UART AND GPS
serial = busio.UART(board.TX, board.RX, baudrate=9600, timeout=1, receiver_buffer_size=1024)
gps = adafruit_gps.GPS(serial, debug=False)
gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
gps.send_command(b'PMTK220,1000')

while not gps.has_fix:
  gps.update()
  counter_gps += 1
  counter_text.text = '{:04d}'.format(counter_gps)

date_valid = False

while not date_valid:
  gps.update()
  counter_gps += 1
  counter_text.text = '{:04d}'.format(counter_gps)

  if gps.timestamp_utc.tm_year != 0:
    date_valid=True

clock.datetime = time.struct_time((gps.timestamp_utc.tm_year, gps.timestamp_utc.tm_mon, gps.timestamp_utc.tm_mday, gps.timestamp_utc.tm_hour, gps.timestamp_utc.tm_min, gps.timestamp_utc.tm_sec, 0, -1, -1))

display_group.remove(counter_text)
display_group.remove(startup_text)

# DISPLAY BATTERY GAUGE
battery_progress_bar = HorizontalProgressBar((112, 0), (16, 8), value=0, min_value=0, max_value=100, fill_color=0x000000, outline_color=0xFFFFFF, bar_color=0x00FF00, direction=HorizontalFillDirection.LEFT_TO_RIGHT)
display_group.append(battery_progress_bar)

# DISPLAY TIME AND DATE FIELDS
default_utc_clock_text = '00:00:00 UTC'
utc_clock_text = label.Label(font, text=default_utc_clock_text, color=clock_color, x=0, y=3)
display_group.append(utc_clock_text)

default_utc_date_text = 'SUN JAN 01, 2020'
utc_date_text = label.Label(font, text=default_utc_date_text, color=date_color, x=0, y=14)
display_group.append(utc_date_text)

default_tz_clock_text = '00:00:00 ' + timezone_desc[0]
tz_clock_text = label.Label(font, text=default_tz_clock_text, color=clock_color, x=0, y=30)
display_group.append(tz_clock_text)

default_tz_date_text = 'SUN JAN 01, 2020'
tz_date_text = label.Label(font, text=default_tz_date_text, color=date_color, x=0, y=41)
display_group.append(tz_date_text)

# DISPLAY LATITUDE / LONGITUDE / ALTITUDE / GRID / COMPASS FIELDS
default_lat_text = 'Lat:    0.0000'
lat_text = label.Label(font, text=default_lat_text, color=location_color, x=0, y=57)
display_group.append(lat_text)

default_grid_text = '      '
grid_text = label.Label(font, text=default_grid_text, color=grid_color, x=93, y=57)
display_group.append(grid_text)

default_lon_text = 'Lon:    0.0000'
lon_text = label.Label(font, text=default_lon_text, color=location_color, x=0, y=68)
display_group.append(lon_text)

default_compass_text = '---'
compass_text = label.Label(font, text=default_compass_text, color=grid_color, x=111, y=68)
display_group.append(compass_text)

default_alt_text = 'Alt:     0 FT     0 M'
alt_text = label.Label(font, text=default_alt_text, color=location_color, x=0, y=84)
display_group.append(alt_text)

# DISPLAY GPS STATISTICS
default_move_text = 'Spd:     0 Ang:     0'
move_text = label.Label(font, text=default_move_text, color=location_color, x=0, y=100)
display_group.append(move_text)

default_sat_count_text = 'Satellites: 0 '
sat_count_text = label.Label(font, text=default_sat_count_text, color=sat_color, x=0, y=123)
display_group.append(sat_count_text)

# CALCULATE AND FORMAT UTC TIME, UTC DATE, TIMEZONE TIME AND TIMEZONE DATE. CALCULATE DST
class calc_datetime:
  def __init__(self, base_time_secs):
    time_utc_tuple=time.localtime(base_time_secs)

    # CHECK FOR DEC 31 / JAN 1 OVERLAP AND CORRECT YEAR FOR TIMEZONE DATE
    base_year = time_utc_tuple[0]
    error_check_tuple = (base_year, 1, 1, 0, 0, 0, 0, 0, 0)
    error_check_secs = time.mktime(error_check_tuple) - timezone_offset * 86400

    if base_time_secs < error_check_secs:
      base_year -= 1

    # CALCULATE IN SECONDS THE DST START TIME AND DATE
    dst_start_tuple = (base_year, dst_start[0], dst_start[1] * 7 - 6, dst_start[3], 0, 0, 0, 0, 0)
    dst_start_secs = time.mktime(dst_start_tuple)
    dst_start_tuple = time.localtime(dst_start_secs)

    dst_start_diff = dst_start[2] - dst_start_tuple[6]

    if dst_start_diff < 0:
      dst_start_diff += 7

    dst_start_secs += dst_start_diff * 86400

    # CALCULATE IN SECONDS THE DST END TIME AND DATE
    dst_end_tuple = (base_year, dst_end[0], dst_end[1] * 7 - 6, dst_end[3], 0, 0, 0, 0, 0)
    dst_end_secs = time.mktime(dst_end_tuple) - dst_offset
    dst_end_tuple = time.localtime(dst_end_secs)

    dst_end_diff = dst_end[2] - dst_end_tuple[6]

    if dst_end_diff < 0:
      dst_end_diff += 7

    dst_end_secs += dst_end_diff * 86400

    # IF THE CURRENT TIME AND DATE FALL BETWEEN THE DST START AND END TIMES, SET DST_ACTIVE
    if base_time_secs >= dst_start_secs and base_time_secs < dst_end_secs:
      dst_active = True
    else:
      dst_active = False

    # FORMAT UTC DATA
    self.utc_date = '{} {} {:02d}, {}'.format(day_text[time_utc_tuple[6]],month_text[time_utc_tuple[1]],time_utc_tuple[2],time_utc_tuple[0])
    self.utc_time = '{:02d}:{:02d}:{:02d} UTC'.format(time_utc_tuple[3],time_utc_tuple[4],time_utc_tuple[5])

    # CALCULATE TIMEZONE TIME AND DATE
    time_tz_secs = base_time_secs + timezone_offset * 3600 + dst_active * dst_offset
    time_tz_tuple = time.localtime(time_tz_secs)

    # FORMAT TIMEZONE DATA
    self.tz_date = '{} {} {:02d}, {}'.format(day_text[time_tz_tuple[6]],month_text[time_tz_tuple[1]],time_tz_tuple[2],time_tz_tuple[0])
    self.tz_time = '{:02d}:{:02d}:{:02d} {}'.format(time_tz_tuple[3],time_tz_tuple[4],time_tz_tuple[5],timezone_desc[dst_active])

# CALCULATE MAIDENHEAD GRID SQUARE BASED ON CURRENT LAT / LON
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
  last_utc_time = ''
  last_utc_date = ''
  last_tz_time = ''
  last_tz_date = ''
  last_grid_sq = ''
  last_lat = ''
  last_lon = ''
  last_alt = ''
  last_sat = 0
  last_speed = 0
  last_angle = 0
  last_compass = ''
  last_battery_time = -30
  last_battery_percent = 0
  battery_average_list = []

  for i in range(battery_list_elements):
    battery_average_list.append(battery.value)

  while True:
    gps.update()

    current_lat = gps.latitude
    current_lon = gps.longitude

    if gps.altitude_m is not None:
      current_alt = int(gps.altitude_m)
    else:
      current_alt = 0

    if gps.speed_knots is not None:
      current_speed = int(gps.speed_knots * 1.15078)
    else:
      current_speed = 0

    if gps.track_angle_deg is not None:
      current_angle = int(gps.track_angle_deg)
    else:
      current_angle = 0

    if gps.satellites is not None:
      current_sat = gps.satellites
    else:
      current_sat = 0

        # GET CURRENT FORMATTED TIME AND DATE, UPDATE LABELS IF ANY HAVE CHANGED
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

        # GET CURRENT GRID SQUARE, UPDATE LAT, LON AND GRID LABELS IF DATA HAS CHANGED
    current_grid_sq = calc_position(35.5844,-78.5171)

    if last_lat != current_lat:
      pad_length = 8 - len('{0:.4f}'.format(current_lat))
      lat_text.text = 'Lat:  ' + ' '*pad_length + '{0:.4f}'.format(current_lat)
      last_lat = current_lat

    if last_lon != current_lon:
      pad_length = 9 - len('{0:.4f}'.format(current_lon))
      lon_text.text = 'Lon: ' +  ' '*pad_length + '{0:.4f}'.format(current_lon)
      last_lon = current_lon

    if last_grid_sq != current_grid_sq:
      grid_text.text = current_grid_sq
      last_grid_sq = current_grid_sq

        # UPDATE ALTITUDE LABEL IF DATA HAS CHANGED
    if last_alt != current_alt:
      alt_feet = int(current_alt * 3.28084)
      meter_pad_length = 5 - len(str(current_alt))
      feet_pad_length = 5 - len(str(alt_feet))
      alt_text.text = 'Alt: ' + ' '*feet_pad_length + str(alt_feet) + ' FT ' + ' '*meter_pad_length + str(current_alt) + ' M'
      last_alt = current_alt

        # UPDATE SPEED AND TRACK ANGLE LABEL IF DATA HAS CHANGED
    if (last_speed != current_speed) or (last_angle != current_angle):
      speed_pad_length = 5 - len(str(current_speed))
      last_speed = current_speed

      angle_pad_length = 5 - len(str(current_angle))
      last_angle = current_angle
      move_text.text = 'Spd: ' + ' '*speed_pad_length + str(current_speed) + ' Ang: ' + ' '*angle_pad_length + str(current_angle)

        # UPDATE SATELLITE COUNT LABEL IF DATA HAS CHANGED
    if last_sat != current_sat:
      sat_count_text.text = 'Satellites: ' + str(current_sat)
      last_sat = current_sat

        # CHECK MAGNETOMETER AND UPDATE LABEL IS DATA HAS CHANGED
    x, y, z = compass.magnetic

    if y > 0:
      angle = 90 - math.atan(x/y) * 180 / math.pi
    elif y < 0:
      angle = 270 - math.atan(x/y) * 180 / math.pi
    elif (x < 0) and (y == 0):
      angle = 180
    elif (x > 0) and (y == 0):
      angle = 0
    else:
      angle = -1

    if (angle < 11.25) or (angle >= 348.75):
      current_compass = 'N'
    else:
      for i in range(15):
        c_angle = compass_angle[i]

        if (angle >= c_angle) and (angle < (c_angle + 22.5)):
          current_compass = compass_point[i]
          break

    if last_compass != current_compass:
      pad_length = 3 - len(current_compass)
      compass_text.text = ' '*pad_length + current_compass
      last_compass = current_compass

        # CHECK BATTERY VOLTAGE AND CALCULATE PERCENTAGE OF CHARGE
    current_battery_time = time.monotonic()

    if (current_battery_time - last_battery_time) > 30:
      last_battery_time = current_battery_time

      battery_average_list.pop(0)
      battery_average_list.append(battery.value)
      battery_average = 0

      for i in battery_average_list:
        battery_average += i

      battery_average = battery_average / battery_list_elements
      current_battery_percent = 0

      for percent in range(10, 1, -1):
        if battery_average <= battery_level[percent] and battery_average > battery_level[percent - 1]:
          current_battery_percent = (percent + 1) * 10
          break

      # UPDATE BATTERY GAUGE IF PERCENTAGE HAS CHANGED
      if last_battery_percent != current_battery_percent:
        battery_progress_bar.bar_color = battery_colors[current_battery_percent - 1]
        battery_progress_bar.value = current_battery_percent
        last_battery_percent = current_battery_percent

    serial.reset_input_buffer()

main()
