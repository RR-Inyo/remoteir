#!/usr/bin/python3
# -*- coding: utf-8 -*-

# remotier/__init__.py
# (c) 2021 Shigenori Inoue
# A Python script to:
# - define Flask object "app"
# - load config
# - import views

from flask import Flask

app = Flask(__name__)
app.config.from_object('remoteir.config')

from remoteir.views import views
