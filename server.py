#!/usr/bin/python3
# -*- coding: utf-8 -*-

# server.py
# (c) 2021 Shigenori Inoue
# A Python script to run the web server for Remoteir

from remoteir import app

if __name__ == '__main__':
    app.run(host = '0.0.0.0', threaded = True)
