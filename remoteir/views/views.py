#!/usr/bin/python3 -*- coding: utf-8 -*-

# remoteir/views/views.py
# (c) 2021 Shigenori Inoue
# A Python script to:
# - control HTML content
# - control IR signal transmitters
# - control temperature and humidity sensor

# Import modules to manipulate CSV file
import pandas as pd
import csv

# Import modules for Flask web app
from flask import request, redirect, url_for, render_template, make_response, flash, session
from remoteir import app
import datetime
import time

# Import Matplotlib and related modules
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Import modules for IR remote controller and DHT22 (aka AM2302) sensor
import pigpio
from lib import irxmit, irlightPanasonic, iracPanasonic

# Define pigpio instance
pi = pigpio.pi()

# Define instances for IR remote controller
GPIO_IR = 13
T_WAIT = 0.3
ir = irxmit.IRxmit(GPIO_IR, host = 'localhost', format = 'AEHA')
ac = iracPanasonic.IRACPanasonic(ir)
lightDining = irlightPanasonic.IRlightPanasonic(ir, ch = 1)
lightLiving = irlightPanasonic.IRlightPanasonic(ir, ch = 2)

# Define filename to read DHT22 data
CSV_FILE = '/tmp/DHT22_record.csv'

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] != app.config['PASSWORD']:
            flash('パスワードが異なります')
        else:
            session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(minutes = 30)
            session['logged_in'] = True
            flash('ログインしました')
            return redirect(url_for('show_dashboard'))
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('ログアウトしました')
    return redirect(url_for('show_dashboard'))

# Root, the dashboard
@app.route('/')
def show_dashboard():
    # Check logged-in status
    if not session.get('logged_in'):
        return redirect('/login')

    # Get temperature and humidity data acquired by DHT22
    # Read tail of CSV file and obtain latest data
    df = pd.read_table(CSV_FILE)
    latest = df.tail(1).values
    t_raw = latest[0, 0]
    t = datetime.datetime.strptime(t_raw, '%Y-%m-%d %H:%M:%S.%f')
    t_srt = t.strftime('%Y/%m/%d %H:%M')
    temp = latest[0, 1]
    humid = latest[0, 2]
    env = {'time': t_srt, 'temp_c': temp, 'humidity': humid}

    return render_template('index.html', env = env)

# Air conditioner control
@app.route('/ac', methods=['POST'])
def acControl():
    # Check logged-in status
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get values from form
    tempsetting = int(request.form['tempsetting'])
    command = request.form['command']

    # Send IR command to air conditoner
    if command == 'heating':
        ac.on_heating(tempsetting)
        msg = f'{tempsetting}°C設定で暖房運転を開始しました'
    elif command == 'cooling':
        if tempsetting >= 20:
            ac.on_cooling(tempsetting)
            msg = f'{tempsetting}°C設定で冷房運転を開始しました'
        else:
            msg = 'エラー！ 冷房の場合，温度を20°C以上に設定して下さい'
    elif command == 'drying':
        ac.on_drying(tempsetting)
        msg = f'{tempsetting}°C設定でドライ運転を開始しました'
    elif command == 'off':
        ac.off()
        msg = 'エアコンを停止しました'

    # Wait for a short time
    time.sleep(T_WAIT)

    # Return to dashboard
    flash(msg)
    return redirect(url_for('show_dashboard'))

# Light at dining control
@app.route('/lightDining', methods=['POST'])
def lightDiningControl():
    # Check logged-in status
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get values from form
    command = request.form['command']

    # Send IR command to the light
    if command == 'on':
        lightDining.on()
        msg = 'ダイニングの照明を点灯しました'
    elif command == 'full':
        lightDining.full()
        msg = 'ダイニングの照明を全灯にしました'
    elif command == 'night':
        lightDining.night()
        msg = 'ダイニングの照明を常夜灯にしました'
    elif command == 'off':
        lightDining.off()
        msg = 'ダイニングの照明を消灯しました'

    # Wait for a short time
    time.sleep(T_WAIT)

    # Return to dashboard
    flash(msg)
    return redirect(url_for('show_dashboard'))

# Light at living control
@app.route('/lightLiving', methods=['POST'])
def lightLivingControl():
    # Check logged-in status
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get values from form
    command = request.form['command']

    # Send IR command to the light
    if command == 'on':
        lightLiving.on()
        msg = 'リビングの照明を点灯しました'
    elif command == 'full':
        lightLiving.full()
        msg = 'リビングの照明を全灯にしました'
    elif command == 'night':
        lightLiving.night()
        msg = 'リビングの照明を常夜灯にしました'
    elif command == 'off':
        lightLiving.off()
        msg = 'リビングの照明を消灯しました'

    # Wait for a short time
    time.sleep(T_WAIT)

    # Return to dashboard
    flash(msg)
    return redirect(url_for('show_dashboard'))

# PNG image of temperature and humidity trend graph made by Matplotlib
@app.route('/graph.png')
def graph():

    # Define graph and font sizes
    G_WIDTH = 6
    G_HEIGHT = 4
    G_FONTSIZE = 14
    G_FONT_FAMILY = 'IPAexGothic'

    # Read CSV file
    with open('/tmp/DHT22_record.csv') as f:
        reader = csv.reader(f, delimiter = '\t')
        t, temp, humid = [], [], []
        for l in reader:
            t.append(datetime.datetime.strptime(l[0], '%Y-%m-%d %H:%M:%S.%f'))
            temp.append(float(l[1]))
            humid.append(float(l[2]))

    # Define Matplotlib graph handler and adjustment
    fig, ax = plt.subplots(2, 1, figsize = (G_WIDTH, G_HEIGHT))
    #fig.patch.set_facecolor('lavender')
    plt.subplots_adjust(left = 0.1, right = 0.95, bottom = 0.15, top = 0.95)
    plt.rcParams['font.family'] = G_FONT_FAMILY
    plt.rcParams["font.size"] = G_FONTSIZE
    plt.subplots_adjust(hspace = 0.1)

    # Set datetime format
    if len(t) < 360:    # Data less than 6 hours
        tick = 1
    elif len(t) < 720:  # Data less than 12 hours
        tick = 3
    elif len(t) < 1440: # Data less than 24 hours
        tick = 6
    elif len(t) < 2160: # Data less than 36 hours
        tick = 8
    elif len(t) < 2880: # Data less than 48 hours
        tick = 12
    else:               # Data equal to or longer than 48 hours
        tick = 24
    xloc = mdates.HourLocator(byhour = range(0, 24, tick), tz = None)
    xfmt = mdates.DateFormatter('%m/%d\n%H:%M')

    # Plot temperature
    ax[0].fill_between(t, temp, color = 'firebrick', alpha = 0.2)
    ax[0].plot(t, temp, label = '温度 [°C]', color = 'firebrick')
    ax[0].xaxis.set_major_locator(xloc)
    ax[0].xaxis.set_major_formatter(xfmt)
    ax[0].axes.xaxis.set_ticklabels([])
    ax[0].set_ylim(5, 35)
    ax[0].legend(loc = 'lower left')
    ax[0].grid()

    # Plot humidity
    ax[1].fill_between(t, humid, color = 'royalblue', alpha = 0.2)
    ax[1].plot(t, humid, label = '湿度 [%]', color = 'royalblue')
    ax[1].xaxis.set_major_locator(xloc)
    ax[1].xaxis.set_major_formatter(xfmt)
    ax[1].set_ylim(10, 70)
    ax[1].legend(loc = 'lower left')
    ax[1].grid()

    # Output figure to canvas
    canvas = FigureCanvasAgg(fig)
    buf = BytesIO()
    canvas.print_png(buf)
    data = buf.getvalue()

    # Generate and return response
    response = make_response(data)
    response.headers['Content-Type'] = 'image/png'
    response.headers['Content-Length'] = len(data)
    return response
