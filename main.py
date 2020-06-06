
from google.cloud import datastore
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

# This disables the requirement to use HTTPS so that you can test locally.
import os 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
client = datastore.Client()

BOATS = "boats"

# These should be copied from an OAuth2 Credential section at
# https://console.cloud.google.com/apis/credentials
client_id = "467068889594-acc65qdnts17iif94o2a6dnt2vc8vtao.apps.googleusercontent.com"
client_secret = "p5MPAhZQ_t67xT9WYNo7Xw6q"

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
redirect_uri = 'https://mini-bookie.wl.r.appspot.com/oauth'

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
scope = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
             'https://www.googleapis.com/auth/userinfo.profile']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                          scope=scope)

#error handler from Piazza
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

#Verification handler adopted from
def verify_jwt(request):
    try:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
        req = requests.Request()
        id_info = id_token.verify_oauth2_token( 
        token, req, client_id)
        return id_info['email']
    except:
        return ''

# This link will redirect users to begin the OAuth flow with Google
@app.route('/')
def index():
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account")
    return 'Please go <a href=%s>here</a> and authorize access.' % authorization_url

# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@app.route('/oauth')
def oauthroute():
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token( 
    token['id_token'], req, client_id)

    return "Your JWT is: %s" % token['id_token']


@app.route('/boats', methods=['POST', 'GET'])
def boats_post():
    if request.method == 'POST':
        payload = verify_jwt(request)
        if len(payload) == 0:
            return ("INVALID JWT", 401)
        content = request.get_json()
        if 'name' not in content.keys():
            return("need a name", 400)
        if 'type' not in content.keys():
            return("need a type", 400)
        if 'length' not in content.keys():
            return("need a length", 400)
        new_boat = datastore.entity.Entity(key=client.key(BOATS))
        new_boat.update({'name': content['name'], 'type': content['type'], 'length': content['length'], 'owner': payload})
        client.put(new_boat)
        return (str(new_boat.key.id), 201)
    elif request.method == 'GET':
        query = client.query(kind=BOATS)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        return json.dumps(results)
    else:
        return ("Method not supported", 405)

@app.route('/boats/<id>', methods=['DELETE'])
def boats_delete(id):
    if request.method == 'DELETE':
        boatOwner = verify_jwt(request)
        if len(boatOwner) == 0:
            return('Need an authorization', 401)
        boat_key = client.key(BOATS, int(id))
        boat = client.get(key=boat_key)
        if boat is None:
            return('Invalid boat ID', 403)
        elif boat["owner"] != boatOwner:
            return('Not your boat guy', 403)
        else:
            client.delete(boat_key)
            return ('', 204)
    else:
        return ('Method not recogonized', 405)

#Rubric vs Piazza post @140 was confusing so I secured this route per rubcric
@app.route('/owners/<id>/boats', methods=['GET'])
def boats_owner_get(id):
    if request.method == 'GET':
        boatOwner = verify_jwt(request)
        if len(boatOwner) == 0:
            return('Need an authorization', 401)
        if boatOwner != id:
            return('Can only see your own boats here', 401)
        query = client.query(kind=BOATS)
        query.add_filter('owner', '=', id)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        return json.dumps(results)
    else:
        return ('Method not recogonized', 405)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)