# -*- encoding: utf-8 -*-
"""
Light Bootstrap Dashboard - coded in Flask

Author  : AppSeed App Generator
Design  : Creative-Tim.com
License : MIT 
Support : https://appseed.us/support 
"""

from flask               import render_template, request, url_for, redirect, flash
from flask_login         import login_user, logout_user, current_user, login_required
from werkzeug.exceptions import HTTPException, NotFound, abort
from werkzeug.security   import generate_password_hash
from werkzeug.security   import check_password_hash

from app        import app, lm, db, bc
from app.models import User, SensorData, Hardware
from app.forms  import LoginForm, RegisterForm
import psycopg2 
from datetime import datetime
from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent="Bikota")

units = {
    "Temperature" : "°C",
    "Humidity" : "%H",
    "CO2" : "PPM",
    "Pressure" : "hPa",
    "PM10" : "PPM",
    "PM25" : "PPM"
}

total_sensors = 0

statuses = {
    "Parked",
    "Rented",
    "Defect",
    "Offline"
}

chart_colors = ["112, 214, 96", 
                "255,102,102",
                "245,206,66", 
                "75,192,192", 
                "123, 152, 237",
                "222, 129, 227",
                "75,192,192", 
                "245,206,66", 
                "112, 214, 96", 
                "123, 152, 237",
                "222, 129, 227"]

db_host='db.dev.iota.pw'
db_port=6000
database='arp_b'
user='arp_b'
password='iota999'

def connect_DB():
    try:        
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(host=db_host, port=db_port, user=user, password=password, database=database)
        print("Successfully connected to DB")
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return -1

conn = connect_DB()

def exec_query(msg, num_values):
    print("""Executing SQL query on Database server...""")
    
    cur = conn.cursor()
    cur.execute(msg)
    conn.commit()
    res = cur.fetchall()
    if res:
        if num_values == 1:
            res = [r[0] for r in res]
            print('Success. Database connection closed.')
            return res
        elif num_values == 2:
            timestamp = []
            #values = []
            selector_data = []
            for row in res:
                timestamp.append(row[0])
                selector_data.append(row[1])
            #values.append(selector_data)
            print('Success. Database connection closed.')
            return timestamp, selector_data
        else:
            timestamp = []
            values = []
            for row in res:
                timestamp.append(row[0])
            for index in range (1, num_values):
                selector_data = []
                for row in res:
                    selector_data.append(row[index])
                values.append(selector_data)
            print('Success. Database connection closed.')
            return timestamp, values
    else:
        print("Error while executing SQL query: {}".format(msg))
        return -1
        

def query_data_default(table, selectors, hw_id, limit=50):
    query = 'SELECT "timestamp", '
    for selector in selectors:
        query += '"{}" , '.format(selector)
    query  = query[:-2] + ' FROM (SELECT "timestamp", EXTRACT(SECOND FROM "timestamp") AS "seconds", '
    for selector in selectors:
        query += '"{}" , '.format(selector)
    query = query[:-2] + 'FROM public."{}" WHERE "hardwareID" = {} AND '.format(table, hw_id)
    for selector in selectors:
        query += '"{}" IS NOT NULL AND '.format(selector)
    query = query[:-4] + 'ORDER BY "timestamp" DESC) AS TEMP_TABLE WHERE MOD(CAST(TEMP_TABLE."seconds" AS INT), 5) = 0 ORDER BY TEMP_TABLE."timestamp" ASC '
    if limit:
        query += 'LIMIT {} '.format(limit)
    #print(query)
    print("""Executing SQL query on Database server...""")
    return exec_query(query, len(selectors)+1)

def query_data_range(table, selector, hw_id, date_range, interval="1 hour", date_format_str = "DD.MM.YYYY HH24:MI:SS"):
    query = 'SELECT * FROM (SELECT "timestamp", "{}" '.format(selector)
    query += 'FROM public."{}" WHERE "hardwareID" = {} AND '.format(table, hw_id)
    query += '"{}" IS NOT NULL AND '.format(selector)
    if len(date_range) > 1:
        query += """"timestamp" BETWEEN TO_TIMESTAMP('{0}','{2}') AND TO_TIMESTAMP('{1}','{2}') ORDER BY "timestamp" DESC) AS TEMP_TABLE ORDER BY TEMP_TABLE."timestamp" ASC""".format(date_range[0], date_range[1], date_format_str)
    elif len(date_range) == 1:
        query += """ "timestamp" BETWEEN TO_TIMESTAMP('{0}','{2}') - interval '{1}' AND TO_TIMESTAMP('{0}','{2}') ORDER BY "timestamp" DESC) AS TEMP_TABLE ORDER BY TEMP_TABLE."timestamp" ASC""".format(date_range[0], interval, date_format_str)
    print(query)
    return exec_query(query,2)

def query_data_addr(table, selector, hw_id, addr):
    query = 'SELECT "timestamp", "{0}" FROM (SELECT "timestamp", "address", "{0}" '.format(selector)
    query += 'FROM public."{}" WHERE "hardwareID" = {} AND '.format(table, hw_id)
    query += '"{}" IS NOT NULL AND '.format(selector)
    query += """ "address" = '{}' ORDER BY "timestamp" DESC) AS TEMP_TABLE ORDER BY TEMP_TABLE."timestamp" ASC """.format(addr)
    print("""Executing SQL query on Database server...""")
    return exec_query(query, 2)

def get_hw_ids(table="SENSOR_DATA"):
    print("""Getting all hardware IDs...""")
    msg = """SELECT DISTINCT "hardwareID" FROM public."{}" WHERE "hardwareID" is NOT NULL ORDER BY "hardwareID" """.format(table)
    return exec_query(msg,1)

# provide login manager with load_user callback
@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# authenticate user
@app.route('/logout.html')
def logout():
    logout_user()
    flash("Successfully logged out", "success")
    return redirect('/login.html')

# register user
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    
    # declare the Registration Form
    form = RegisterForm(request.form)

    msg = None

    if request.method == 'GET': 

        return render_template('layouts/default.html',
                                content=render_template( 'pages/register.html', form=form) )

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password) 
        email = request.form["email"]

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = User.query.filter_by(email=email).first()

        if user or user_by_email:
            if user:
                msg = 'Error: User {} already exists!'.format(username)
            elif user_by_email:
                 msg = 'Error: Email {} already exists!'.format(email)
            flash(msg, "danger")
        
        else:         
            data = {"firstname": "",
                    "lastname": "",
                    "address" : "",
                    "city": "",
                    "zip": "",
                    "country": "",
                    "bio": ""
            
            }
            user = User(username, email, pw_hash, data)

            user.save()

            msg = 'User created, please login' 
            flash(msg, "success")
            return render_template('layouts/default.html',
                            content=render_template( 'pages/login.html', form=form) )

    else:
        msg = 'Invalid input'
        flash(msg, "danger")

    return render_template('layouts/default.html',
                            content=render_template( 'pages/register.html', form=form ) )

# authenticate user
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    
    # Declare the login form
    form = LoginForm(request.form)

    # Flask message injected into the page, in case of any errors
    msg = None

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form["username"]
        password = request.form["password"]

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        if user:
            
            #if bc.check_password_hash(user.password, password):
            if check_password_hash(user.password, password):
                login_user(user)
                current_user.user = username
                flash("Successfully logged in", "success")
                return redirect('/')
            else:
                msg = "Invalid password. Please try again."
                flash(msg, "danger")
        else:
            msg = "Invalid username. Please try again."
            flash(msg, "danger")

    return render_template('layouts/default.html',
                            content=render_template( 'pages/login.html', form=form) )

# Render the user page
@app.route('/user.html', methods=['GET', 'POST'])
def user():
    if current_user.is_authenticated:
        if request.method == "POST":
            if request.form["btn"] == "update_profile":
                username = request.form["username"]
                email = request.form["email"]
                user = User.query.filter_by(user=username).first()  #find user by username
                if user:
                    if email != "":
                        user.email = email  #username exists, save new email
                else:
                    user = User.query.filter_by(email=email).first()    #username does not exists, find user by email
                if user:
                    #email exists, save new username and data
                    if username != "":
                        user.user = username    
                    firstname = request.form["first_name"]
                    lastname = request.form["last_name"]
                    address = request.form["address"]
                    city = request.form["city"]
                    zip = request.form["zip"]
                    country = request.form["country"]
                    bio = request.form["desc_text"]
                    user.data = {"firstname": firstname,
                                "lastname": lastname,
                                "address" : address,
                                "city": city,
                                "zip": zip,
                                "country": country,
                                "bio": bio}
                    #update database
                    try:
                        db.session.commit()
                        current_user.user = username
                        flash("Successfully updated profile for user {}".format(username), "success")
                    except Exception as e:
                        print("Error updateing profile for user: ", e)
                        flash("Unable to update profile for user {}. Please make sure inputs are valid".format(username), "danger")
                else:
                    #both username and email do not exist, show error
                    flash("Invalid username or email", "danger")
                    username = current_user.user
            elif request.form["btn"] == "change_pwd":
                username = current_user.user
                user = User.query.filter_by(user=username).first()  #find user by username
                password = request.form["curr_pwd"]
                new_pwd = request.form["new_pwd"]
                if request.form["new_pwd_conf"] == new_pwd:
                    if check_password_hash(user.password, password):
                        user.password = generate_password_hash(new_pwd)
                        try:
                            db.session.commit()
                            flash("Successfully updated password for user {}".format(username), "success")
                        except Exception as e:
                            print("Error changing password for user: ", e)
                            flash("Unable to change password for user {}. Please make sure inputs are valid".format(username), "danger")
                    else:
                        flash("Current password is invalid", "danger")
                else:
                    flash("New passwords do not match", "warning")
            elif request.form["btn"] == "delete_acc":
                username = current_user.user
                user = User.query.filter_by(user=username).first()  #find user by username
                password = request.form["pwd_del"]
                if check_password_hash(user.password, password):
                    try:
                        db.session.delete(user)
                        db.session.commit()
                        flash("Successfully deleted user account {}".format(username), "success")
                    except Exception as e:
                        print("Error deleting user: ", e)
                        flash("Unable to delete user {}. Please make sure inputs are valid".format(username), "danger")
                    return redirect('/login.html')
                else:
                    flash("Password is invalid", "danger")
                
        else:
            # GET request
            if current_user.is_authenticated:
                username = current_user.user
            else:
                flash("Please log in or register to access user profile", "warning")
                return redirect('/login.html')
        # filter User out of database through username
        user = User.query.filter_by(user=username).first()
        data = user.data
        
        return render_template('layouts/default.html',
                                content=render_template( 'pages/user.html', 
                                username = user.user,
                                firstname=data["firstname"], 
                                lastname=data["lastname"], 
                                email=user.email, 
                                address=data["address"],
                                city=data["city"],
                                country = data["country"],
                                zip = data["zip"], 
                                user_desc=data["bio"]))
    else:
        flash("Please log in or register to manage user profile", "warning")
        return redirect('/login.html')

# Render the hardware page
@app.route('/hardware.html', methods=['GET', 'POST'])
def hardware():
    if current_user.is_authenticated:
        location_arr = []
        all_sensors = [sensor for sensor in units] 
        location_str = ""
        hardware_data = db.session.query(Hardware.hardwareID, Hardware.status, Hardware.sensors, Hardware.latitude, Hardware.longitude, Hardware.session_address).order_by(Hardware.hardwareID).all()
        for hardware in hardware_data:
            if hardware[3] is not None and hardware[4] is not None:
                try:
                    location_str = geolocator.reverse("{}, {}".format(hardware[3], hardware[4])).raw["address"]["city"]
                    location_arr.append(location_str)
                except:
                    try: 
                        location_str = geolocator.reverse("{}, {}".format(hardware[3], hardware[4])).raw["address"]["town"]
                        location_arr.append(location_str)
                    except:
                        try:
                            location_str = geolocator.reverse("{}, {}".format(hardware[3], hardware[4])).raw["address"]["state"]
                            location_arr.append(location_str)
                        except Exception as e:
                            location_arr.append("{}, {}".format(hardware[3], hardware[4]))
                            print("Error getting reverse location from latitude and longitude {}, {}: {}".format(hardware[3], hardware[4], e))
                try:
                    print("Updating place column in Hardware Status table")
                    hw = Hardware.query.filter_by(hardwareID=hardware[0]).first()
                    hw.place = location_str
                    db.session.commit()
                except Exception as e:
                    print("Unable to update place column in Hardware Status table for hardware {}: ".format(hardware[0]), e)
            else:
                location_arr.append("No data available")
                        
        if request.method == "POST":
            if request.form["btn"] == "create_hardware":
                hw_id = request.form["new_hw_id"]
                status = request.form["new_status"]
                latitude, longitude, adrr = "", "", ""
                try:
                    location = request.form["new_location"].split(",")
                    latitude = location[0]
                    longitude = location[1]
                except:
                    try:
                        location = request.form["new_location"].split(" ")
                        latitude = location[0]
                        longitude = location[1]
                    except:
                        latitude = None
                        longitude = None
                print(latitude, longitude)
                try:
                    sensors = request.form.getlist("new_sensors")
                except:
                    sensors = None
                try:
                    addr = request.form["new_addr"]
                except:
                    addr = ""

                # filter Hardware out of database through ID
                hardware = Hardware.query.filter_by(hardwareID=hw_id).first()
                if hardware:
                    msg = 'Error: Hardware ID {} already exists!'.format(hw_id)
                    flash(msg, "warning")
                else:
                    try:
                        new_hw = Hardware(hw_id, 0, addr, status, latitude, longitude, sensors)
                        new_hw.save()
                        flash("Successfully created hardware {}".format(hw_id), "success")
                    except Exception as e:
                        print("Error creating hardware: ", e)
                        flash("Unable to create hardware {}. Please make sure inputs are valid".format(hw_id), "danger")
            elif request.form["btn"] == "update_hardware":
                hw_id = request.form["hw_id"]
                hardware = Hardware.query.filter_by(hardwareID=hw_id).first()  
                status = request.form["status"]
                hardware.status = status
                sensors = request.form.getlist("sensors")
                hardware.sensors = sensors
                try:
                    print(request.form["location"])
                    location = request.form["location"].split(",")
                    latitude = location[0]
                    longitude = location[1]
                except:
                    try:
                        print(request.form["location"])
                        location = request.form["location"].split(" ")
                        
                        latitude = location[0]
                        longitude = location[1]
                    except:
                        latitude = None
                        longitude = None
                print(latitude, longitude)
                hardware.latitude = latitude
                hardware.longitude = longitude
                try:
                    db.session.commit()
                    flash("Successfully updated hardware {}".format(hw_id), "success")
                except Exception as e:
                    print("Error updating hardware: ", e)
                    flash("Unable to update hardware {}. Please make sure inputs are valid".format(hw_id), "danger")
            else:
                if "delete_hardware" in request.form["btn"]:
                    print("button: ", request.form["btn"])
                    hw_id = request.form["btn"].split("_")[-1]
                    print("Deleting hardware {}".format(hw_id))
                    try:
                        hardware = Hardware.query.filter_by(hardwareID=hw_id).first() 
                        db.session.delete(hardware)
                        db.session.commit()
                        flash("Successfully deleted hardware {}".format(hw_id), "success")
                    except Exception as e:
                        print("Error deleting hardware: ", e)
                        flash("Unable to delete hardware {}".format(hw_id), "danger")

            return redirect('/hardware.html')
        else:
            return render_template('layouts/default.html',
                                        content=render_template( 'pages/hardware.html',
                                        sensors=all_sensors,
                                        hardware_data = hardware_data,
                                        location_arr = location_arr),
                                    )
    else:
        flash("Please log in or register to manage hardwares", "warning")
        return redirect('/login.html')


# Render the charts page
@app.route('/charts.html', methods=['GET', 'POST'])
def charts():
    if current_user.is_authenticated:
        hw_sensor_addr = dict()
        hw_ids = get_hw_ids()
        all_sensors = [sensor for sensor in units]
        time_unit = "second"
        global unit, chart_colors
        selected_hw_ids = []
        sensors = []
        
        for hw_id in hw_ids:
            hw_data = dict()
            hw_id = "{}".format(hw_id)
            addresses = [hardware.address for hardware in db.session.query(SensorData.address).filter(SensorData.hardwareID==hw_id).distinct().order_by(SensorData.address).all() if hardware.address != ""]
            sensors = db.session.query(Hardware.sensors).filter(Hardware.hardwareID==hw_id).all()[0][0]
            hw_data["addresses"] = addresses
            hw_data["sensors"] = sensors
            print(hw_data)
            hw_sensor_addr[hw_id] = hw_data
        
        if request.method == "POST":
            chart_data = []
            date_range = None
            addr_str = ""
            datetime_str = ""
            x_axis = "Time"
            minutes = 5
            try:
                selected_hw_ids = request.form.getlist("hw_select")
            except:
                selected_hw_ids = []
            try:
                sensors = request.form.getlist("sensor_select")
            except:
                sensors = []        
            try:
                datetime_str =  request.form["datetime_label"]
            except:
                datetime_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            try:
                date_range = datetime_str.split(" - ")
            except:
                date_range = [datetime_str]
            try:
                addr_str = request.form["addr_select"]
            except:
                addr_str = ""
                    
            
            for sensor in sensors:
                data = {}
                data["chart_id"] = "chart_{}".format(sensor)
                data["chart_title"] = sensor
                data["y_axis"] = "{} ({})".format(sensor, units[sensor])
                data["legend"] = []
                data["series"] = []
                if addr_str == "":
                    for hw_id in selected_hw_ids:
                        res = query_data_range("SENSOR_DATA", sensor.lower(), hw_id, date_range)
                        if res is not None:
                            try:
                                datetime_str = "{} - {}".format(res[0][0].strftime("%d.%m.%Y %H:%M:%S"), res[0][len(res[0])-1].strftime("%d.%m.%Y %H:%M:%S"))
                                data["series"].append(res[1])
                                data['labels'] = res[0]
                                data["legend"].append("Hardware {}".format(hw_id)) 
                            except:
                                flash("No data found for hardware {} and sensor {}".format(hw_id, sensor), "warning")
                        else:
                            flash("No data found for hardware {} and sensor {}".format(hw_id, sensor), "warning")
                    if data["series"]:
                        chart_data.append(data)
                elif addr_str != "":
                    data["chart_title"] = "{} of Hardware {}".format(sensor, selected_hw_ids[0]) 
                    data["legend"].append("Session address {}".format(addr_str)) 
                    res = query_data_addr("SENSOR_DATA", sensor.lower(), selected_hw_ids[0], addr_str)
                    if res is not None:
                        try:
                            datetime_str = ""
                            data["series"].append(res[1])
                            data['labels'] = res[0]
                            chart_data.append(data)
                        except:
                            flash("No data found for for hardware {} and sensor {}".format(selected_hw_ids[0], sensor), "warning")
                    else:
                        flash("No data found for session address {} and sensor {}".format(addr_str, sensor), "warning")
            return render_template('layouts/default.html',
                                        content=render_template( 'pages/charts.html',
                                        x_axis = x_axis,
                                        minutes=minutes,
                                        chart_data = chart_data,
                                        sensors=all_sensors,
                                        hw_sensor_addr = hw_sensor_addr,
                                        selected_hw_ids = selected_hw_ids,
                                        selected_sensors = sensors,
                                        selected_addr = [addr_str],
                                        time_unit=time_unit,
                                        chart_colors = chart_colors,
                                        datetime_str=datetime_str),
                                    )                              
                                       
        else:
            return render_template('layouts/default.html',
                                    content=render_template( 'pages/charts.html',
                                    sensors=all_sensors,
                                    hw_sensor_addr = hw_sensor_addr,
                                    time_unit=time_unit),
                                )
    else:
        flash("Please log in or register to access dashboard", "warning")
        return redirect('/login.html')


# Render the map page
@app.route('/map.html', methods=['GET', 'POST'])
def map():
    if current_user.is_authenticated:
        map_points = {
            "Parked": [],
            "Rented": [],
            "Defect": [],
            "Offline": []
        }
        hardware_data = db.session.query(Hardware.hardwareID, Hardware.status, Hardware.latitude, Hardware.longitude).order_by(Hardware.hardwareID).all()
        for hardware in hardware_data:
            if hardware[2] is not None and hardware[3] is not None:
                status = hardware.status[0].upper() + hardware.status[1:]
                map_points[status].append(
                    {
                        "name" : hardware[0],
                        "status" : hardware[1],
                        "lat" : hardware[2],
                        "lon" : hardware[3],
                        "loc" : geolocator.reverse("{}, {}".format(hardware[2], hardware[3])).raw["address"]
                    }
                )
        return render_template('layouts/default.html',
                                    content=render_template( 'pages/map.html',
                                    map_points=map_points),
                                )
    else:
        flash("Please log in or register to access dashboard", "warning")
        return redirect('/login.html')
      

def get_location_dist():
    query = """ SELECT "place", COUNT("hardwareID") FROM public."HARDWARE_STATUS" GROUP BY "place" """
    print("""Getting info of bike distribution by location...""")
    return exec_query(query, 2)

def get_location_by_id():
    query = """ SELECT "hardwareID", "place" FROM public."HARDWARE_STATUS" """
    print("""Getting info of bike location by ID...""")
    return exec_query(query, 2)

def get_sensor_dist():
    data = []
    total_sensors = 0
    for sensor in units:
        query = """ SELECT COUNT("hardwareID") from public."HARDWARE_STATUS" WHERE '{}' = ANY("sensors") """.format(sensor)
        print("""Getting count of sensor {}...""".format(sensor))
        sens_count = exec_query(query, 1)
        data.append(sens_count)
        total_sensors = total_sensors + sens_count[0]
    return data, total_sensors

# App main route + generic routing
@app.route('/', defaults={'path': 'index.html'})
def dashboard(path):
    if current_user.is_authenticated:
        chart_data = []
        # Data for number cards
        total_rides = 0
        for hw_id in get_hw_ids():
            addresses = [hardware.address for hardware in db.session.query(SensorData.address).filter(SensorData.hardwareID==hw_id).distinct() if hardware.address != ""]
            total_rides += len(addresses)
        
        
        # Data for Status Pie Chart
        status_chart = {}
        status_chart["chart_id"] = "status_chart"
        status_chart["chart_title"] = "Hardware Status Statistics"
        status_chart["labels"] = []
        status_chart["data"] = []
        for status in statuses:
            status_chart["labels"].append(status)
            status_chart["data"].append(len(Hardware.query.filter_by(status=status).all()))


        # Data for Distribution by Location Pie Chart
        location_chart = {}
        location_chart["chart_id"] = "dist_by_loc_chart"
        location_chart["chart_title"] = "Bike Distribution By Location"
        location_counts = get_location_dist()
        location_chart["labels"] = ["No location data available" if loc == None else loc for loc in location_counts[0]]
        location_chart["data"] = location_counts[1]

        # Data for Usage by Location Pie Chart
        all_hw_locs = get_location_by_id()
        num_ride_loc = dict.fromkeys(location_chart["labels"], 0)
        no_data_count = 0
        for index, hw_id in enumerate(all_hw_locs[0]):
            addresses = [hardware.address for hardware in db.session.query(SensorData.address).filter(SensorData.hardwareID==hw_id).distinct() if hardware.address != ""]
            place = all_hw_locs[1][index]
            if place == None:
                no_data_count +=1
            else:
                num_ride_loc[place] = len(addresses)
        num_ride_loc["No location data available"] = no_data_count
        usage_chart = {}
        usage_chart["chart_id"] = "usage_by_loc_chart"
        usage_chart["chart_title"] = "Bike Usage By Location"
        usage_chart["labels"] = [key for key in num_ride_loc]
        usage_chart["data"] = list(dict.values(num_ride_loc))

        # Data for Distribution of sensors Pie Chart
        sensor_dist_chart = {}
        sensor_dist_chart["chart_id"] = "sensor_dist_chart"
        sensor_dist_chart["chart_title"] = "Sensor Statistics"
        sensor_dist_chart["labels"] = [sensor for sensor in units]
        sensor_stats = get_sensor_dist()
        sensor_dist_chart["data"] = sensor_stats[0]

        # Add all charts to array
        chart_data.append(status_chart)
        chart_data.append(sensor_dist_chart)
        chart_data.append(location_chart)
        chart_data.append(usage_chart)
        
        
        return render_template('layouts/default.html',
                                    content=render_template( 'pages/index.html',
                                    total_bikes=len(get_hw_ids("HARDWARE_STATUS")),
                                    total_rides=total_rides,
                                    total_sensors=sensor_stats[1],
                                    chart_data=chart_data,
                                    chart_colors=chart_colors) )

    else:  
        return redirect('/login.html')



@app.route('/<path>')
def index(path):
    if current_user.is_authenticated:
        content = None

        try:

            # try to match the pages defined in -> pages/<input file>
            return render_template('layouts/default.html',
                                    content=render_template( 'pages/'+path) )
        except:

            return  render_template('layouts/default.html',
                                    content=render_template('pages/404.html'))
    else:
        
        return redirect('/login.html')
