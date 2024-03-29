#!flask/bin/python
from flask import render_template, flash, redirect, session, url_for, \
        request, g, send_file, abort, jsonify

from flask_admin import Admin
from flask_bootstrap import Bootstrap
from flask_login import current_user
from flask_qrcode import QRcode

from app import app, db, lm
from datetime import datetime, timedelta
from config import STREAMLABS_CLIENT_ID, STREAMLABS_CLIENT_SECRET, \
        CASHTIP_REDIRECT_URI

from .forms import RegisterForm, ProfileForm
from .models import User, PayReq, Transaction

from pycoin.key import Key
from decimal import Decimal
import bitcoin
import requests
import time
import sys
import qrcode
import random
from werkzeug.datastructures import ImmutableOrderedMultiDict


streamlabs_api_url = 'https://www.streamlabs.com/api/v1.0/'
api_token = streamlabs_api_url + 'token'
api_user = streamlabs_api_url + 'user'
api_tips = streamlabs_api_url + "donations"
callback_result = 0

Bootstrap(app)

@app.route('/')
@app.route('/index')
def index():
    if 'nickname' in session:
        if 'social_id' in session:
            nickname=session['nickname']
            try:
                    return render_template(
            'index.html')
            except:
                return redirect(url_for('logout'))

    user_one = random.choice(User.query.all())
    user_two = random.choice(User.query.filter(User.id!=user_one.id).all())
    user_three = random.choice(User.query.filter(User.id!=user_two.id, User.id!=user_one.id).all())
    user_four = random.choice(User.query.filter(User.id!=user_three.id, User.id!=user_two.id, User.id!=user_one.id).all())
    user_five = random.choice(User.query.filter(User.id!=user_four.id, User.id!=user_three.id, User.id!=user_two.id, User.id!=user_one.id).all())
    return render_template(
            'index.html',
            session_nickname=None, userone = user_one, usertwo = user_two, userthree = user_three, userfour = user_four, userfive = user_five)

@app.route('/user/<username>')
def user(username):



    # if 'nickname' in session:
    #     u = User.query.filter_by(social_id=username.lower()).first()
    #     if u:
    #         return render_template(
    #
    #             'user.html',
    #             social_id=session['social_id'],
    #             nickname=session['nickname'],
    #             display_text = u.display_text
    #
    #             )
    u = User.query.filter_by(social_id=username.lower()).first()
    if u:
        try:
            session_nickname = session['nickname']

        except:

            session_nickname = None

        return render_template(

            'user.html',
            session_nickname=session_nickname,
            nickname = u.nickname,
            social_id = u.social_id,
            tx = Transaction.query.order_by(Transaction.timestamp.desc()).all(),
            top5 = Transaction.query.filter_by(token='BCH').order_by(Transaction.amount.desc()).all(),
            display_text = u.display_text,
            user = User.query.filter_by(social_id=username.lower())
            )

    else:
        return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not "social_id" in session:
        return redirect(url_for('index'))
    form = ProfileForm()
    if request.method == "POST":
        u = User.query.filter_by(social_id=session['social_id']).first()

        #xpub
        if form.xpub_field.data:
            if(u.xpub != form.xpub_field.data):
                u.xpub = form.xpub_field.data
                u.latest_derivation = 0

        #text on user page
        if form.user_display_text_field.data:
            u.display_text = form.user_display_text_field.data

        #streamer's paypal email
        if form.paypal_email_field.data:
            u.paypal_email = form.paypal_email_field.data

        if (form.paypal_email_field.data == ""):
            u.paypal_email = ""


        #Image/GIF on donation
        if form.image_ref_field.data:
            u.image_ref = form.image_ref_field.data

        if (form.image_ref_field.data == ""):
            u.image_ref = 'https://media.giphy.com/media/1kTU8a4ehOqydBqk3f/giphy.gif'


        #sound on donation
        if form.sound_ref_field.data:
            u.sound_ref = form.sound_ref_field.data

        if (form.sound_ref_field.data == ""):
            u.sound_ref = 'https://uploads.twitchalerts.com/000/003/774/415/m_health.wav'

        #Image/GIF on donation
        #SLP
        if form.slp_image_ref_field.data:
            u.slp_image_ref = form.slp_image_ref_field.data

        if (form.slp_image_ref_field.data == ""):
            u.slp_image_ref = 'https://media.giphy.com/media/1kTU8a4ehOqydBqk3f/giphy.gif'


        #sound on donation
        #SLP
        if form.slp_sound_ref_field.data:
            u.slp_sound_ref = form.slp_sound_ref_field.data

        if (form.slp_sound_ref_field.data == ""):
            u.slp_sound_ref = 'https://uploads.twitchalerts.com/000/003/774/415/m_health.wav'

        #special text color
        #SLP
        if form.slp_text_color_field.data:
            u.slp_text_color = form.slp_text_color_field.data

        #special text color
        if form.text_color_field.data:
            u.text_color = form.text_color_field.data

        #SLP settings
        if form.slp_ref_field.data:
            print(form.slp_ref_field.data)
            u.slp_ref = form.slp_ref_field.data

        #minimum donation
        if form.min_donation_ref_field.data:
            if(is_number(form.min_donation_ref_field.data)):
                u.min_donation_ref = form.min_donation_ref_field.data
            else:
                u.min_donation_ref = '0.00'

        if (form.min_donation_ref_field.data == ""):
            u.min_donation_ref = '0.00'

        #minimum slp donation
        if form.min_slp_ref_field.data:
            if(is_number(form.min_slp_ref_field.data)):
                u.min_slp_ref = form.min_slp_ref_field.data
            else:
                u.min_slp_ref = '0.0'

        if (form.min_slp_ref_field.data == ""):
            u.min_slp_ref = '0.0'

        db.session.commit()
        nickname=session['nickname']
        return redirect(url_for('user', username=nickname))


    userlist = []
    '''
    userdb = User.query.all()
    for user in userdb:
        userdict = {}
        userdict['name'] = user.nickname
        userdict['num'] = 1
        userlist.append(userdict)
    '''
    userdata = User.query.filter_by(social_id=session['social_id']).first()

    if userdata.paypal_email:
        email = userdata.paypal_email



    return render_template(
            'usersettings.html',
            form=form,
            social_id=session['social_id'],
            nickname=session['nickname'],
            users = userlist,
            xpub = userdata.xpub,
            display_text = userdata.display_text,
            email = userdata.paypal_email,
            sound_ref = userdata.sound_ref,
            color = userdata.text_color,
            image_ref = userdata.image_ref,
            min_donation_ref = userdata.min_donation_ref,
            slp_ref = userdata.slp_ref,
            min_slp_ref = userdata.min_slp_ref,
            slp_sound_ref = userdata.slp_sound_ref,
            slp_image_ref = userdata.slp_image_ref,
            slp_color = userdata.slp_text_color
            )

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    return False

@app.route('/login')
@app.route('/launch')
def login():
    if 'nickname' in session:
        return redirect(url_for('user', username=session['nickname']))

    if request.args.get('code'):
        session.clear()
        authorize_call = {
                'grant_type'    : 'authorization_code',
                'client_id'     : STREAMLABS_CLIENT_ID,
                'client_secret' : STREAMLABS_CLIENT_SECRET,
                'code'          : request.args.get('code'),
                'redirect_uri'  : CASHTIP_REDIRECT_URI
        }

        headers = []

        token_response = requests.post(
                api_token,
                data=authorize_call,
                headers=headers
        )

        token_data = token_response.json()
        print(token_data)
        a_token = token_data['access_token']
        r_token = token_data['refresh_token']

        user_get_call = {
                'access_token' : a_token
        }

        user_access = requests.get(api_user,
                params=user_get_call)

        session.clear()

        try:
            session['social_id'] = user_access.json()['twitch']['name']
            session['nickname'] = user_access.json()['twitch']['display_name']
            session['access_token'] = a_token
            session['refresh_token'] = r_token

            valid_user = User.query.filter_by(social_id=session['social_id']).first()
            if valid_user:
                valid_user.streamlabs_atoken = a_token
                valid_user.streamlabs_rtoken = r_token
                db.session.commit()
                return redirect(url_for('profile'))
            else:
                return redirect(url_for('newuser'))
        except KeyError:
            return redirect(url_for('error'))

    return redirect(
        "https://www.streamlabs.com/api/v1.0/authorize?client_id="+\
        STREAMLABS_CLIENT_ID +
        "&redirect_uri="+ CASHTIP_REDIRECT_URI +
        "&response_type=code"+
        "&scope=donations.create alerts.create", code=302
    )
@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('nickname', None)
    session.pop('social_id', None)
    return redirect(url_for('index'))

@app.route('/newuser', methods=['GET', 'POST'])
def newuser():
    print("entered /newuser")
    form = RegisterForm()

    if 'social_id' in session and request.method == 'POST':
        try:
            new_user = User(
                streamlabs_atoken = session['access_token'],
                streamlabs_rtoken = session['refresh_token'],
                xpub = form.xpub_field.data,
                social_id = session['social_id'],
                nickname = session['nickname'],
                latest_derivation = 0,
                display_text = form.user_display_text_field.data
            )
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('profile'))
        except Exception as e:
            print (str(e))

    try:
        username = session['nickname']
    except KeyError:
        username = "UNKNOWN USERNAME"

    return render_template(
            'register.html',
            form=form)

@app.route('/donatecallback', methods=['GET', 'POST'])
def donatecallback():
    print(request.args)
    return "Hello World!"

@app.errorhandler(404)
def handle404(e):
    return render_template(
            '404.html',
            users = User.query.all()
            )

@app.route('/twitch/<username>')
def twitch(username):
    return redirect(
        "https://www.twitch.tv/"+username

    )

@app.route('/about')
def about():
    return render_template(
            'about.html',
            users = User.query.all()
    )

@app.route('/how')
def how():
    return render_template(
            'how.html',
            users = User.query.all()
    )

@app.route('/users')
def users():
    return render_template('users.html', users = User.query.all(), page = 1, min = 1, max = 21, prevpage = 0, nextpage = 2)

@app.route('/users/<pagenum>')
def users_page(pagenum):
    min_count = int(pagenum) * 20 - 19
    max_count = int(pagenum) * 20 + 1
    prev = 0

    if(int(pagenum) == 1):
        prev = 0
    else:
        prev = int(pagenum) - 1

    next = int(pagenum) + 1
    return render_template('users.html', users = User.query.all(), page = pagenum, min = min_count, max = max_count, prevpage = prev, nextpage = next)

@app.route('/history')
def history():
     return render_template(
            'history.html',
            tx = Transaction.query.order_by(Transaction.timestamp.desc()).all(),
            users = User.query.all()
    )

@app.route('/error')
def error():
    return render_template(
            'error.html',
            users = User.query.all()
            )

