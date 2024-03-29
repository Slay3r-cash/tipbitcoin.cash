#!flask/bin/python
from flask import render_template, flash, redirect, session, url_for, \
        request, g, send_file, abort, jsonify

from flask_login import current_user
from flask_qrcode import QRcode

from app import app, db, lm
from datetime import datetime, timedelta
from config import STREAMLABS_CLIENT_ID, STREAMLABS_CLIENT_SECRET, \
        CASHTIP_REDIRECT_URI

from .forms import RegisterForm, ProfileForm
from .models import User, PayReq, Transaction

from pycoin.key import Key
from pycoin.key.validate import is_address_valid
from exchanges.bch_price import get_bch_price
from decimal import Decimal
from .payment import check_payment_on_address, check_address_history
import pprint
import urllib.request, json
import bitcoin
import requests
import time
import sys
import qrcode
import os
import random
from werkzeug.datastructures import ImmutableOrderedMultiDict

streamlabs_api_url = 'https://www.streamlabs.com/api/v1.0/'
api_token = streamlabs_api_url + 'token'
api_user = streamlabs_api_url + 'user'
api_tips = streamlabs_api_url + "donations"
api_custom = streamlabs_api_url + "alerts"
callback_result = 0

def read_server_list():
    with open("servers.json", 'r') as f:
        return json.loads(f.read())

def grab_random_server(serverList):
    serverAddress = None
    while (serverAddress == None):
        serverAddress = random.choice(list(serverList))
        serverObject = serverList[serverAddress]
        if 't' in serverObject:
            serverPort = serverObject['t']
        elif 's' in serverObject:
            serverPort = serverObject['s']
        else:
            serverAddress = None
    print(serverAddress + ":" + serverPort)
    return {
            'serverAddress': str(serverAddress),
            'serverPort'   : int(serverPort)
            }

def get_spice_amount(tx_hash):
    try:
        with urllib.request.urlopen("https://bch.coin.space/api/tx/"+tx_hash) as url:
            if(url.getcode() == 200):
                data = json.loads(url.read().decode())
                for index, item in enumerate(data['vout']):
                    output = item['scriptPubKey']['asm']

                    if(output.startswith("OP_RETURN")):
                        output_array = output.split()
                        token = output_array[4]
                        if(token == "4de69e374a8ed21cbddd47f2338cc0f479dc58daa2bbe11cd604ca488eca0ddf"):
                            print(output_array[5])
                            amount_sent = int(output_array[5], 16)
                            amount_sent_formatted = amount_sent/100000000
                            print(amount_sent_formatted)
                            return amount_sent_formatted
                        else:
                            return 0.0
    except urllib.error.HTTPError as e:
        return get_spice_amount(tx_hash)

@app.route('/_verify_payment', methods=['POST'])
def verify_payment():
    btc_addr = request.form['btc_addr']
    social_id = request.form['social_id']
    db.session.commit()
    payrec_check = PayReq.query.filter_by(addr=btc_addr).first()
    serverList = read_server_list()
    randomServer = grab_random_server(serverList)
    randomAddress = randomServer['serverAddress']
    randomPort = randomServer['serverPort']
    print("PAYMENT CHECK")
    history_check = check_address_history(btc_addr, randomAddress, randomPort)
    payment_check_return = {
            'transaction_found': None,
            'payment_verified' : "FALSE",
            'user_display'     : User.query.filter_by(
                social_id=social_id
                ).first().nickname
    }
    print("***" + "checking for history on: " + btc_addr + "***\n")
    if history_check and payrec_check:
        payment_check_return['payment_verified'] = "TRUE"
        print("Payment Found!")
        amount = check_payment_on_address(btc_addr, randomAddress, randomPort)
        print(amount)
        payment_check_return['transaction_found'] = history_check[0]['tx_hash']

        payment_notify(social_id,
                payrec_check,
                amount,
                history_check[0]['tx_hash'],
                btc_addr)

        db.session.delete(payrec_check)
        db.session.commit()
    return jsonify(payment_check_return)

def payment_notify(social_id, payrec, balance, txhash, grs_addr):
    user = User.query.filter_by(social_id=social_id).first()
    print(balance)
    if(balance == 546):
        spice_amount = get_spice_amount(txhash)
        print(spice_amount)
        if(spice_amount != 0.0):
            token_call = {
                            'grant_type'    : 'refresh_token',
                            'client_id'     : STREAMLABS_CLIENT_ID,
                            'client_secret' : STREAMLABS_CLIENT_SECRET,
                            'refresh_token' : user.streamlabs_rtoken,
                            'redirect_uri'  : CASHTIP_REDIRECT_URI
            }
            headers = []
            #print("Acquiring Streamlabs Access Tokens")
            tip_response = requests.post(api_token, data=token_call, headers=headers).json()
            #print("Tokens Acquired, Committing to Database")

            user.streamlabs_rtoken = tip_response['refresh_token']
            user.streamlabs_atoken = tip_response['access_token']
            db.session.commit()

            if payrec.user_message:
                msg=payrec.user_message
            else:
                msg=''

            spice_amount_display = "{0:.8f}".format(spice_amount).rstrip("0")
            donation = "*" + payrec.user_display + "* donated *" + spice_amount_display + " SPICE*!\n"
            tip_call = {
                    'type'       : 'donation',
                    'message'    : donation,
                    'user_message' : msg,
                    'image_href' : user.slp_image_ref,
                    'sound_href' : user.slp_sound_ref,
                    'duration'   : 5000,
                    'special_text_color' : user.slp_text_color,
                    'access_token' : tip_response['access_token']
            }
            print(tip_call)
            min_slp_float = float(user.min_slp_ref)
            if spice_amount >= min_slp_float:
                tip_check_alert = requests.post(api_custom, data=tip_call, headers=headers).json()
                print(tip_check_alert)

            print("Saving transaction data in database...")
            payreq = PayReq.query.filter_by(addr=grs_addr).first()
            new_transaction = Transaction(twi_user=payreq.user_display, twi_message=payreq.user_message, user_id=social_id, tx_id=txhash, amount=str(spice_amount), timestamp=payreq.timestamp, token="SPICE")
            db.session.add(new_transaction)
            db.session.commit()

            print("Transaction data saved!")
            print("Donation Alert Sent")
            return "spice.flow"
        else:
            return "not.spice"
    else:
        grs_amount = ((balance) /100000000)

        usd_price = float(get_bch_price())
        value = grs_amount * usd_price

        usd_two_places = float(format(value, '.2f'))
        #print(usd_two_places)
        token_call = {
                        'grant_type'    : 'refresh_token',
                        'client_id'     : STREAMLABS_CLIENT_ID,
                        'client_secret' : STREAMLABS_CLIENT_SECRET,
                        'refresh_token' : user.streamlabs_rtoken,
                        'redirect_uri'  : CASHTIP_REDIRECT_URI
        }
        headers = []
        #print("Acquiring Streamlabs Access Tokens")
        tip_response = requests.post(api_token, data=token_call, headers=headers).json()
        #print("Tokens Acquired, Committing to Database")

        user.streamlabs_rtoken = tip_response['refresh_token']
        user.streamlabs_atoken = tip_response['access_token']
        db.session.commit()

        grs_amount_display = " ("+ str(grs_amount) +" BCH Donated)"

        if payrec.user_message:
            msg=payrec.user_message

        else:
            msg=''

        tip_call = {
                'name'       : payrec.user_display,
                'identifier' : payrec.user_identifier,
                'message'    : msg+grs_amount_display,
                'amount'     : usd_two_places,
                'currency'   : 'USD',
                'access_token' : tip_response['access_token'],
                'skip_alert' : 'yes'
        }
        tip_check = requests.post(api_tips, data=tip_call, headers=headers).json()
        donation = "*" + payrec.user_display + "* donated *$" + str(usd_two_places) + "* in BCH!\n"
        tip_call = {
                'type'       : 'donation',
                'message'    : donation,
                'user_message' : msg,
                'image_href' : user.image_ref,
                'sound_href' : user.sound_ref,
                'duration'   : 5000,
                'special_text_color' : user.text_color,
                'access_token' : tip_response['access_token']
        }
        print(tip_call)

        min_amount = str(user.min_donation_ref)
        print(min_amount)
        if min_amount == 'None':
            tip_check_alert = requests.post(api_custom, data=tip_call, headers=headers).json()
            print(tip_check_alert)
        else:
            min_amount_float = float(user.min_donation_ref)
            if usd_two_places >= min_amount_float:
                tip_check_alert = requests.post(api_custom, data=tip_call, headers=headers).json()
                print(tip_check_alert)

        # custom_notify(social_id, payrec.user_message, value, usd_two_places)
        print("Saving transaction data in database...")
        # transaction = Transaction.query.filter_by(addr=btc_addr).first()
        payreq = PayReq.query.filter_by(addr=grs_addr).first()
        new_transaction = Transaction(twi_user=payreq.user_display, twi_message=payreq.user_message, user_id=social_id, tx_id=txhash, amount=str(grs_amount), timestamp=payreq.timestamp, token="BCH")
        db.session.add(new_transaction)
        db.session.commit()

        print("Transaction data saved!")
        print("Donation Alert Sent")
        return tip_check.__str__()

@app.route('/_create_payreq', methods=['POST'])
def create_payment_request():
    social_id = request.form['social_id']
    deriv = User.query.filter_by(social_id = social_id).first(). \
            latest_derivation
    address = get_unused_address(social_id, deriv)
    new_payment_request = PayReq(
            address,
            user_display=request.form['user_display'],
            user_identifier=request.form['user_identifier']+"_grs",
            user_message=request.form['user_message']
            )
    db.session.add(new_payment_request)
    db.session.commit()
    return jsonify(
            {'btc_addr': address}
            )

@app.route('/tip/<username>')
def tip(username):
    u = User.query.filter_by(social_id=username.lower()).first()
    if u:
        try:
            session_nickname = session['nickname']

        except:

            session_nickname = None

        dono_str = u.min_donation_ref
        return render_template('tipv2.html', session_nickname=session_nickname, nickname = u.nickname, social_id = u.social_id, display_text = u.display_text, email = u.paypal_email, dono = u.min_donation_ref, slp_ref = u.slp_ref, slp_dono = u.min_slp_ref)
    else:
        return render_template(

            '404.html',
            username=username
            )

def get_unused_address(social_id, deriv):
    '''
    Need to be careful about when to move up the latest_derivation listing.
    Figure only incrementing the database entry when blockchain activity is
    found is the least likely to create large gaps of empty addresses in
    someone's BTC Wallet.
    '''
    serverList = read_server_list()
    randomServer = grab_random_server(serverList)
    randomAddress = randomServer['serverAddress']
    randomPort = randomServer['serverPort']

    pp = pprint.PrettyPrinter(indent=2)
    userdata = User.query.filter_by(social_id = social_id).first()

    # Pull BTC Address from given user data
    key = Key.from_text(userdata.xpub).subkey(0). \
            subkey(deriv)

    address = key.address(use_uncompressed=False)

    # Check for existing payment request, delete if older than 5m.
    payment_request = PayReq.query.filter_by(addr=address).first()
    if payment_request:
        req_timestamp = payment_request.timestamp
        now_timestamp = datetime.utcnow()
        delta_timestamp = now_timestamp - req_timestamp
        if delta_timestamp > timedelta(seconds=60*5):
            db.session.delete(payment_request)
            db.session.commit()
            payment_request = None

    if not check_address_history(address, randomAddress, randomPort):
        if not payment_request:
            return address
        else:
            print("Address has payment request...")
            print("Address Derivation: ", deriv)
            return get_unused_address(social_id, deriv + 1)
    else:
        print("Address has blockchain history, searching new address...")
        print("Address Derivation: ", userdata.latest_derivation)
        userdata.latest_derivation = userdata.latest_derivation + 1
        db.session.commit()
        return get_unused_address(social_id, deriv + 1)

@app.route('/_test_alert', methods=['POST'])
def send_test_alert():
    social_id = request.form['social_id']
    user = User.query.filter_by(social_id=social_id).first()
    grs_amount = ((65000) /100000000)

    usd_price = float(get_bch_price())
    value = grs_amount * usd_price

    usd_two_places = float(format(value, '.2f'))
    #print(usd_two_places)
    token_call = {
                    'grant_type'    : 'refresh_token',
                    'client_id'     : STREAMLABS_CLIENT_ID,
                    'client_secret' : STREAMLABS_CLIENT_SECRET,
                    'refresh_token' : user.streamlabs_rtoken,
                    'redirect_uri'  : CASHTIP_REDIRECT_URI
    }
    headers = []
    #print("Acquiring Streamlabs Access Tokens")
    tip_response = requests.post(
            api_token,
            data=token_call,
            headers=headers
    ).json()
    #print("Tokens Acquired, Committing to Database")

    user.streamlabs_rtoken = tip_response['refresh_token']
    user.streamlabs_atoken = tip_response['access_token']
    db.session.commit()

    grs_amount_display = " ("+ str('%g' % grs_amount) +" BCH Donated)"
    msg='Example message!'

    donation = "*John Doe* donated *$" + str(usd_two_places) + "* in BCH! \n"
    tip_call = {
            'type'       : 'donation',
            'message'    : donation,
            'user_message' : msg,
            'image_href' : user.image_ref,
            'sound_href' : user.sound_ref,
            'duration'   : 5000,
            'special_text_color' : user.text_color,
            'access_token' : tip_response['access_token']
    }
    print(tip_call)

    tip_check_alert = requests.post(api_custom, data=tip_call, headers=headers).json()
    print(tip_check_alert)
    return tip_call.__str__()

@app.route('/_test_alert_slp', methods=['POST'])
def send_test_alert_slp():
    social_id = request.form['social_id']
    user = User.query.filter_by(social_id=social_id).first()
    grs_amount = ((123000000) /100000000)

    #print(usd_two_places)
    token_call = {
                    'grant_type'    : 'refresh_token',
                    'client_id'     : STREAMLABS_CLIENT_ID,
                    'client_secret' : STREAMLABS_CLIENT_SECRET,
                    'refresh_token' : user.streamlabs_rtoken,
                    'redirect_uri'  : CASHTIP_REDIRECT_URI
    }
    headers = []
    #print("Acquiring Streamlabs Access Tokens")
    tip_response = requests.post(
            api_token,
            data=token_call,
            headers=headers
    ).json()
    #print("Tokens Acquired, Committing to Database")

    user.streamlabs_rtoken = tip_response['refresh_token']
    user.streamlabs_atoken = tip_response['access_token']
    db.session.commit()

    msg='Example message!'

    donation = "*John Doe* donated *" + str(grs_amount) + " SPICE*! \n"
    tip_call = {
            'type'       : 'donation',
            'message'    : donation,
            'user_message' : msg,
            'image_href' : user.slp_image_ref,
            'sound_href' : user.slp_sound_ref,
            'duration'   : 5000,
            'special_text_color' : user.slp_text_color,
            'access_token' : tip_response['access_token']
    }
    print(tip_call)

    tip_check_alert = requests.post(api_custom, data=tip_call, headers=headers).json()

    return tip_call.__str__()
