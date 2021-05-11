from flask import Flask, jsonify, send_from_directory
from flask import render_template, redirect, session
from flask import request, g, make_response
from flask_mail import Mail, Message
from flask_cors import *
from flask_apscheduler import *
import datetime
import functools
import sqlite3
import logging
import time

##password = input("Please enter the email password: ")

app = Flask(__name__)
app.secret_key = "H4cK3dByA10n3"
CORS(app,  resources={r"/*": {"origins": "*"}}) 
DATABASE = "database/nursingHome.db"
app.config.update(
    DEBUG = False,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PROT=587,
    MAIL_USE_TLS = True,
    MAIL_USERNAME = 'bsccisproject@gmail.com',
    MAIL_PASSWORD = 'Sem@2project'
)
mail = Mail(app)
scheduler = APScheduler()

def get_short_time(t):
    return t[11:16]

def get_time_now():
    t = time.localtime()
    return '%04d-%02d-%02d %02d:%02d:%02d' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

def send_email(addr, title, content):
    msg = Message(
        title,
        sender="bsccisproject@gmail.com",
        recipients=[addr],
    )
    msg.body = content
    with app.app_context():
        mail.send(msg)

def notifyNurser(info):
    db = sqlite3.connect(DATABASE)
    with app.app_context():
        selectResult = query_db("SELECT * FROM personalInfo WHERE personType=2;", db=db)
        db.close()
        print(selectResult)
        email_addr_list = []
        for nurse in selectResult:
            email = nurse["emailAddress"]
            print('send  eamil to '+ email, info)
            send_email(email, 'Medicine Giving Alert', str(info))
        # email_addr_list.append(selectResult[0]["emailAddress"])

def dailyNotifyNurser():
    print('==========================dailyNotifyNurser================================')
    db = sqlite3.connect(DATABASE)
    selectResult = query_db("SELECT NAME, loginID FROM personalInfo WHERE personType=3", db=db)
    db.close()
    for t in selectResult:
        db = sqlite3.connect(DATABASE)
        selectResult = query_db('SELECT time FROM scheduledMedicineTime WHERE loginID=?', args=(t['loginID'], ), db=db)
        db.close()
        time_list = [x['time'] for x in selectResult]
        cur_time = time.localtime()
        for tm in time_list:
            if int(tm[:2]) == cur_time.tm_hour and int(tm[3:5]) == cur_time.tm_min:
                db = sqlite3.connect(DATABASE)
                query_db('INSERT INTO medicineRecord VALUES (?, ?)', (t['loginID'], get_time_now()[:-3]), db=db)
                db.commit()
                db.close()
                t['scheduledMedicineTime'] = time_list
                notifyNurser(t)
                break
    print('========================================================================')

def connect_db():
    return sqlite3.connect(DATABASE)

def query_db(query, args=(), one=False, db=None):
    print(query, args)
    if not db:
        db = g.db
    try:
        cur = db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(e)
        return []

def get_tb_names():
    tbs = query_db('select name from sqlite_master where type = "table"')
    return [x['name'] for x in tbs]

def get_tb_colums(tb_name):
    tbs = get_tb_names()
    if tb_name not in  tbs:
        return []
    cols = query_db("SELECT name FROM PRAGMA_TABLE_INFO('%s');" % tb_name)
    cols = [x['name'] for x in cols]
    print(cols)
    return cols

def commit_db():
    g.db.commit()

def update_db(tb_name, items, filters):
    keys = items.keys()
    filter_keys = filters.keys()
    
    # check 
    cols = get_tb_colums(tb_name)
    for x in list(keys) + list(filter_keys):
        if x not in cols:
            return False
    
    filters_text = ' WHERE ' + ' AND '.join(['%s=?' % key for key in filter_keys])
    sql = 'UPDATE %s SET ' % (tb_name) + ', '.join(['%s=?' % key for key in keys]) + filters_text
    args = list(items.values()) + list(filters.values())
    query_db(sql, args)
    commit_db()
    return True

def insert_db(tb_name, d):
    cols = get_tb_colums(tb_name)
    for x in d.keys():
        if x not in cols:
            print("ERROR", '`' + x + '`', "invalid colum")
            return False
    query_db('INSERT INTO %s (%s) VALUES (%s)' % (tb_name, ', '.join(list(d.keys())), ', '.join(['?'] * len(d))), tuple(d.values()))
    commit_db()
    return True

def delete_db(tb_name, filters):
    filter_keys = filters.keys()
    
    # check 
    cols = get_tb_colums(tb_name)
    for x in list(filter_keys):
        if x not in cols:
            return False
    
    filters_text = ' WHERE ' + ' AND '.join(['%s=?' % key for key in filter_keys])
    sql = 'DELETE FROM %s' % (tb_name) + filters_text
    args = tuple(filters.values())
    query_db(sql, args)
    commit_db()
    return True

def validCheck(_types):
    def check(func):
        @functools.wraps(func)
        def inner2(*args,**kwargs):
            UUID = session.get('token')
            print('validCheck', _types, UUID)
            selectResult = query_db("SELECT personType FROM PersonalInfo WHERE UUID=?", (UUID,))
            for _type in _types:
                if len(selectResult) > 0 and selectResult[0]["personType"] == _type:
                    return func(*args,**kwargs)
            return redirect("/")
        return inner2
    return check

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

def allow_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'OPTIONS,HEAD,GET,POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with'
    return resp

def auth_by_token(token):
    res = query_db("SELECT loginID, personType FROM PersonalInfo WHERE UUID=?", (token,))
    if len(res) > 0:
        return res[0]['loginID'], res[0]['personType']
    return None, None

@app.route("/api/v1/login", methods = ['POST'], endpoint='l1')
def loginApi():
    loginParams = request.json
    userID = loginParams['id']
    userPasswd = loginParams['password']
    selectResult = query_db("SELECT loginPasswd, personType, UUID FROM PersonalInfo WHERE loginID=?", (userID,))

    if len(selectResult) > 0 and userPasswd == selectResult[0]["loginPasswd"]:
        truePasswd = selectResult[0]["loginPasswd"]
        pType = selectResult[0]["personType"]
        token = selectResult[0]["UUID"]
        
        session["token"] = token 
        resultJson = {
            "status": 0,
            "redirectUrl": ""
        }
        if pType == 1:
            resultJson["redirectUrl"] = "/manager"
        elif pType == 2:
            resultJson["redirectUrl"] = "/nurse"
        elif pType == 3:
            resultJson["redirectUrl"] = "/elder"
        return make_response(jsonify(resultJson), 200)
    else:
        resultJson = {
            "status": 1,
            "message": "Invalid userID or Password!"
        }

    response = make_response(jsonify(resultJson))
    response = allow_cors(response)
    return response

@app.route("/api/v1/setElderPhisicalInfo", methods = ['POST'])
@validCheck([2])
def setElderPhisicalInfo():
    Params = request.json
    selectResult = query_db("SELECT personType FROM PersonalInfo WHERE loginID=?", (Params["loginID"],))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(
            jsonify(
                {
                    "status": 1,
                    "message": "This elder does not exist!"
                }
            )
        )
    query_db("INSERT INTO phisicalRecord VALUES (?, ?, ?, ?, ?)", (
        Params["loginID"],
        Params["data"]["recordDate"],
        Params["data"]["bloodPressureLow"],
        Params["data"]["bloodPressureHigh"],
        Params["data"]["heartBeat"]
    ))
    commit_db()
    return make_response(jsonify({"status": 0}))

@app.route("/api/v1/setElderMedicineInfo", methods = ['POST'])
@validCheck([1])
def setElderMedicineInfoApi():
    Params = request.json
    selectResult = query_db("SELECT personType FROM PersonalInfo WHERE loginID=?", (Params["loginID"],))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(
            jsonify(
                {
                    "status": 1,
                    "message": "This elder does not exist!"
                }
            )
        )
    query_db('DELETE FROM scheduledMedicineTime WHERE loginID=?', (Params['loginID'],))
    commit_db()
    for t in Params["scheduledMedicineTime"]:
        query_db('INSERT INTO scheduledMedicineTime VALUES (?, ?)', (Params['loginID'], t))
    commit_db()

    selectResult = query_db("SELECT NAME, loginID FROM PersonalInfo WHERE personType=3 and loginID=?", (Params['loginID'],))
    info = selectResult[0]
    selectResult = query_db('SELECT time FROM scheduledMedicineTime WHERE loginID=?', (Params['loginID'],))
    info['scheduledMedicineTime'] = selectResult
    notifyNurser(info)
    return make_response(jsonify({"status": 0}))

@app.route("/api/v1/setElderPersonalInfo", methods = ['POST'])
@validCheck([1])
def setElderPersonalInfoApi():
    Params = request.json
    selectResult = query_db("SELECT personType FROM PersonalInfo WHERE loginID=?", (Params["loginID"],))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(
            jsonify(
                {
                    "status": 1,
                    "message": "This elder does not exist!"
                }
            )
        )
    info = Params
    loginID = info['loginID']
    del(info['loginID'])
    update_db('PersonalInfo', info, {'loginID': loginID})
    commit_db()
    return make_response(jsonify({"status": 0}))

@app.route("/api/v1/checkRfid", methods = ['POST'])
def checkRfid():
    Params = request.json
    selectResult = query_db("SELECT loginID, NAME, personType, UUID FROM PersonalInfo WHERE RFIDInfo=?", (Params["uid"],))
    if len(selectResult) == 0:
        return make_response(jsonify({"status": 1, "message": "Invalid RFIDInfo!"}))
    loginID = selectResult[0]['loginID']
    token = selectResult[0]['UUID']
    session["token"] = token
    query_db('INSERT INTO gateRecord VALUES (?, ?, ?)', (loginID, get_time_now(), Params['isGetIn']))
    commit_db()
    return make_response(jsonify(
        {
            "status": 0,
            'data': {
                'name': selectResult[0]["NAME"],
                "type": selectResult[0]["personType"]
            }
        }
    ))

@app.route("/api/v1/getElderList", methods = ['GET'])
@validCheck([1, 2])
def getElderListApi():
    selectResult = query_db("SELECT loginID FROM PersonalInfo WHERE personType=3")
    resultList = [selectResult[i]["loginID"] for i in range(len(selectResult))]
    return make_response(
        jsonify(
            {
                "status": 0,
                'data': {
                    'loginID': resultList
                }
            }
        )
    )

@app.route("/api/v1/getElderInfo_elder", methods = ['GET'])
@validCheck([3])
def getElderInfo_elderApi():
    # Params = request.json
    token = session.get('token')
    # print('token -> ' + token)
    selectResult = query_db("SELECT loginID, personType, forbiddenFood FROM PersonalInfo WHERE UUID=?", (token,))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(jsonify({"status": 1, "message": "Not exists!"}))
    loginID = selectResult[0]['loginID']
    forbiddenFood = selectResult[0]['forbiddenFood']
    dailyRecords = query_db("SELECT date, bloodPressureLow, bloodPressureHigh, heartbeat FROM phisicalRecord WHERE loginID=\'{}\'".format(loginID))
    medicineRecords = query_db("SELECT time FROM medicineRecord WHERE loginID=?", (loginID,))
    return make_response(jsonify(
        {
            "status": 0,
            "data": {
                'dailyRecords': dailyRecords,
                'medicineRecords': medicineRecords,
                'forbiddenFood': forbiddenFood
            }
        }
    ))

@app.route("/api/v1/getElderInfo_manager", methods = ['POST'])
@validCheck([1])
def getElderInfo_managerApi():
    Params = request.json
    selectResult = query_db("SELECT forbiddenFood, personType, NAME, AGE, faceInfo, Description, inDate, isMale FROM PersonalInfo WHERE loginID=?", (Params["loginID"],))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(jsonify({"status": 1, "message": "Not exists!"}))
    medicineRecords = query_db("SELECT time FROM medicineRecord WHERE loginID=?", (Params["loginID"],))
    gateRecords = query_db("SELECT time, isGetIn FROM gateRecord WHERE loginID=?", (Params["loginID"],))
    eatMedicineTime = query_db('SELECT time FROM scheduledMedicineTime WHERE loginID=?', (Params['loginID'],))
    # eatMedicineTime = query_db("SELECT scheduledMedicineTime FROM PersonalInfo WHERE loginID=?", (Params['loginID'],))
    # print(eatMedicineTime)
    # eatMedicineTime = eatMedicineTime[0]['scheduledMedicineTime'] if len(eatMedicineTime) > 0 else None
    # if eatMedicineTime:
    #     eatMedicineTime = eatMedicineTime[11:16]
    return make_response(jsonify(
        {
            "status": 0,
            "data": {
                "name": selectResult[0]["NAME"],
                "age": selectResult[0]["AGE"],
                "pictures": selectResult[0]["faceInfo"],
                "Description": selectResult[0]["Description"],
                "medicineRecords": medicineRecords,
                "gateRecords": gateRecords,
                "eatMedicineTime": [x['time'] for x in eatMedicineTime],
                'inDate': selectResult[0]['inDate'],
                'isMale': selectResult[0]['isMale'],
                'forbiddenFood': selectResult[0]['forbiddenFood']
            }
        }
    ))

@app.route("/api/v1/getElderInfo_nurse", methods = ['POST'])
@validCheck([2])
def getElderInfo_nurseApi():
    Params = request.json
    selectResult = query_db("SELECT name, personType, forbiddenFood, Description FROM PersonalInfo WHERE loginID=?", (Params["loginID"],))
    if len(selectResult) == 0 or selectResult[0]["personType"] != 3:
        return make_response(jsonify({"status": 1, "message": "Not exists!"}))
    medicineRecords = query_db("SELECT time FROM medicineRecord WHERE loginID=?", (Params["loginID"],))
    gateRecords = query_db("SELECT time, isGetIn FROM gateRecord WHERE loginID=?", (Params["loginID"],))
    return make_response(jsonify(
        {
            "status": 0,
            "data": {
                "forbiddenFood": selectResult[0]["forbiddenFood"],
                "Description": selectResult[0]["Description"],
                "gateRecords": gateRecords,
                "medicineRecords": medicineRecords,
                "name": selectResult[0]["NAME"]
            }
        }
    ))


@app.route("/api/v1/checkRfid", methods=['POST'])
def checkRfidApi():
    params = request.json
    if 'uid' not in params:
        return allow_cors(
            make_response(
                jsonify({'status': 1, 'message': 'invalid request'})))
    # TODO: query rfid uid
    selectResult = query_db("SELECT NAME, personType FROM PersonalInfo WHERE RFIDInfo=?", (params['uid'],))
    if len(selectResult) == 0:
        return allow_cors(
            make_response(
                jsonify({'status': 2, 'message': 'uid not found'})))
    name = selectResult[0]["NAME"]
    personType = selectResult[0]["personType"]
    return allow_cors(
        make_response(
            jsonify({'status': 0, 'data': {'name': name, 'type': personType}})))
    
@app.route("/manager", methods = ['GET'])
@validCheck([1])
def managerIndex():
    return redirect("/front/manager.html")

@app.route("/nurse", methods = ['GET'])
@validCheck([2])
def nurseIndex():
    return redirect("/front/nurse.html")

@app.route("/elder", methods = ['GET'])
@validCheck([3])
def elderIndex():
    return redirect("/front/elder.html")

@app.route('/front/<path:path>')
def front(path):
    return send_from_directory('front', path)

@app.route('/')
def index():
    token = session.get('token')
    if token:
        _id, _type = auth_by_token(token)
        if _id:
            return [None, 
                redirect('/manager'),
                redirect('/nusre'),
                redirect('/elder')][_type]
    return redirect('/front/index.html')

@app.route('/files/<path:path>')
def downloadFiles(path):
    return send_from_directory('files', path)


@app.route('/api/v1/getFaceInfo', methods=['POST'])
def getFaceInfoApi():
    params = request.json
    loginID = params['loginID']
    key = params['key']
    if key != 'f39d0847-8e10-4de4-be45-9260da87794e':
        return make_response({'status': 1, 'message': 'key wrong'})
    res = query_db('SELECT faceInfo FROM PersonalInfo WHERE loginID=?', (loginID,))
    url = res[0]['faceInfo']
    return make_response({'status': 0, 'data': {'url': '/files/' + url}})

@app.route("/api/v1/addElder", methods = ['POST'])
@validCheck([1])
def addElderApi():
    params = request.json
    params['elder']['personType'] = 3
    params['elder']['lastSetPasswd'] = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
    if insert_db('PersonalInfo', params['elder']):
        return make_response({'status': 0})
    else:
        return make_response({'status': 1, 'message': '?'})

@app.route("/api/v1/delElder", methods = ['POST'])
@validCheck([1])
def delElderApi():
    params = request.json
    if delete_db('PersonalInfo', {'loginID': params['loginID']}):
        return make_response({'status': 0})
    else:
        return make_response({'status': 1, 'message': '?'})

@app.route("/api/v1/isTimeToChangePasswd", methods = ['GET'])
@validCheck([1, 2, 3])
def isTimeToChangePasswdApi():
    uuid = session.get('token')
    res = query_db('SELECT lastSetPasswd FROM PersonalInfo WHERE UUID=?', (uuid,))
    if len(res) > 0:
        t = res[0]['lastSetPasswd']
        print(t)
        last_time = datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
        de = datetime.datetime.now() - last_time
        if de.days > 90:
            return make_response({
                'status': 0,
                'data': {'days': de.days, 'needSet': True}
            })
        else:
            return make_response({
                'status': 0,
                'data': {'days': de.days, 'needSet': False}
            })
    return make_response({
        'status': 1,
        'message': 'No such user!'
    })

@app.route("/api/v1/setPassword", methods=['POST'])
@validCheck([1, 2, 3])
def setPasswordApi():
    params = request.json
    token = session.get('token')
    if update_db('PersonalInfo', 
                 {'loginPasswd': params['passwd'], 'lastSetPasswd': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')}, 
                 {'UUID': token}):
        return make_response({'status': 0})
    else:
        return make_response({'status': 1, 'message': 'failed'})


def start_scheduler_later(scheduler):
    def start_t(scheduler):
        left = 60 - time.localtime().tm_sec
        print("==================schedule will start %d seconds later==============" % left)
        time.sleep(left)
        scheduler.start()
        print("=========================schedule started===========================")
    import threading
    t = threading.Thread(target=start_t, args=(scheduler,))
    t.start()

if __name__ == "__main__":
    # with app.test_request_context():
    #     app.preprocess_request()
    scheduler.init_app(app)
    scheduler.add_job(func=dailyNotifyNurser, args=(), id='1', trigger='interval', 
        minutes=1, replace_existing=True)
    # scheduler.start()
    start_scheduler_later(scheduler)
    app.run(host="0.0.0.0", port=8809)
