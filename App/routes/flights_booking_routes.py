from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from App.models.Flightmodels import FlightSchedule, AirportData
from App.code.utils.flightradar24 import get_flight_info
import datetime
from ..exts import db

flights_booking = Blueprint('flights_booking', __name__, url_prefix='/flights_booking')