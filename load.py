from flask import Blueprint, request
from google.cloud import datastore
import verificationHelper
import json
import constants

client = datastore.Client()

bp = Blueprint('load', __name__, url_prefix='/loads')


@bp.route('/', methods=['POST', 'GET'])
def loads_get_post():
    if request.method == 'POST':
        content = request.get_json()
        payload = verificationHelper.verify_jwt(request)
        if len(payload) == 0:
            return ("INVALID JWT", 401)
        if 'destination' not in content.keys():
            return("need a destination", 400)
        if 'weight' not in content.keys():
            return("need a weight", 400)
        if 'contents' not in content.keys():
            return("need to know contents", 400)
        new_load = datastore.entity.Entity(key=client.key(constants.loads))
        new_load.update({'owner': payload, 'weight': content['weight'],
          'contents': content['contents'], 'destination': content['destination'],
          'boat': ''})
        client.put(new_load)
        return (str(new_load.key.id), 201)
    elif request.method == 'GET':
        query = client.query(kind=constants.loads)
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('offset', '0'))
        g_iterator = query.fetch(limit= q_limit, offset=q_offset)
        pages = g_iterator.pages
        results = list(next(pages))
        if g_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        for e in results:
            e["self"] = request.host_url + 'loads/' + str(e.key.id)
        output = {"loads": results}
        if next_url:
            output["next"] = next_url
        return json.dumps(output)


@bp.route('/<id>', methods=['DELETE', 'GET', 'PATCH'])
def loads_put_delete(id):
    if request.method == 'DELETE':
        content = request.get_json()
        payload = verificationHelper.verify_jwt(request)
        if len(payload) == 0:
            return ("INVALID JWT", 401)
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return('Invalid load ID', 404)
        elif load['owner'] != payload:
            return('Not your load to delete', 403)
        elif load['boat'] == '':
            client.delete(load_key)
            return('', 204)
        else:
            boat_key = client.key(constants.boats, int(load['boat']))
            boat = client.get(key=boat_key)
            boat['loads'].remove(str(id))
            client.put(boat)
            client.delete(load_key)
            return ('', 204)
    elif request.method == 'GET':
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return('Invalid load ID', 404)
        else:
            return (load, 200)
    if request.method == 'PATCH':
        content = request.get_json()
        payload = verificationHelper.verify_jwt(request)
        if len(payload) == 0:
            return ("INVALID JWT", 401)
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return('Invalid load ID', 404)
        elif load['owner'] != payload:
            return('Not your load to edit', 403)
        content = request.get_json()
        if 'weight' not in content.keys():
            return('I only edit weight', 400)
        else:
            load["weight"] = content["weight"]
            client.put(load)
            return(load, 200)
    else:
        return ('Method not recogonized', 405)