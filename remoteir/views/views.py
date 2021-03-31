#!/usr/bin/python3 -*- coding: utf-8 -*-

# remoteir/views/views.py
# (c) 2021 Shigenori Inoue
# A Python script to:
# - control HTML content
# - control IR signal transmitters
# - control temperature and humidity sensor

# Import modules to manipulate files
import sys
import os
import pathlib

# Import modules for Flask web app
from flask import request, redirect, url_for, render_template, flash, session
from remoteir import app
import datetime
import time

# Import modules for IR remote controller and DHT22 (aka AM2302) sensor
import pigpio
from pigpio_dht import DHT22
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

# Define instances for DHT22 sensor
GPIO_DHT22 = 19
LOCKFILE = 'DHT22_lock'
TIMEOUT = 1
dht22 = DHT22(GPIO_DHT22, timeout_secs = TIMEOUT, pi = pi)
t_prev = datetime.datetime.now()

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

    # Get values from temperature humidity sensor
    now = datetime.datetime.now()
    nowtxt = f'{now.year:04d}/{now.month:02d}/{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}'

    # Avoid TimeoutError exception from DHT22
    try:
        # Wait until lock file is removed
        while os.path.exists(LOCKFILE):
            print(f'DHT22 is busy. Wait for {T_WAIT} sec.')
            time.sleep(T_WAIT)

        # Create lock file
        pathlib.Path(LOCKFILE).touch()

        # Read sensor
        env = dht22.read(retries = 3)

        # Remove lock file
        os.remove(LOCKFILE)

    except (TimeoutError, AssertionError):
        # Set dummy data if exception raised
        env = {'temp_c': 0, 'temp_f': 0, 'humidity': 0, 'valid': True}

    return render_template('index.html', nowtxt = nowtxt, env = env)

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
