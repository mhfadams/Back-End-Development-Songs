from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
from bson.json_util import dumps, LEGACY_JSON_OPTIONS
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/health", methods=["GET"])
def health():
    return {"status":"OK"}

@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})

    return {"count": count}, 200

@app.route("/song")
def song():
    results = db.songs.find({})
    song_list = []
    for result in results:
        song_list.append(dumps(result))
    return {"songs": song_list}, 200

@app.route("/song/<id>")
def get_song_by_id(id):
    result = db.songs.find_one({"id": int(id)})
    if ( result != None ):
        return dumps(result), 200
    else:
        return {"message": f"song with id:{id} not found"}, 404


@app.route("/song", methods=["POST"])
def create_song():
    song_data = {"id":0, "title":"", "lyrics":""}
    #song_data["id"] = (db.songs.count_documents({}) + 1)
    song_data["id"] = int(request.json["id"])
    if (db.songs.find_one({ "id": song_data["id"] }) != None):
        return {"Message": f"song with id {song_data['id']} already present"}, 302
    song_data["title"] = request.json["title"]
    song_data["lyrics"] = request.json["lyrics"]
    result = db.songs.insert_one(song_data)
    if result:
        return {"inserted id": dumps(result.inserted_id) }, 200
    return "Unknown error", 404

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song_data = {"id":0, "title":"", "lyrics":""}
    #song_data["id"] = (db.songs.count_documents({}) + 1)
    song_data["id"] = int(id)
    if (db.songs.find_one({ "id": song_data["id"] }) == None):
        return {"message": "song not found"}, 404
    song_data["title"] = request.json["title"]
    song_data["lyrics"] = request.json["lyrics"]
    result = db.songs.update_one({"id": song_data["id"]}, {'$set': song_data})
    if result and (result.modified_count > 0):
        return dumps(db.songs.find_one({ "id": song_data["id"] })), 200
    return {"message":"song found, but nothing updated"}, 200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    song_data = {"id":0, "title":"", "lyrics":""}
    #song_data["id"] = (db.songs.count_documents({}) + 1)
    song_data["id"] = int(id)
    if (db.songs.find_one({ "id": song_data["id"] }) == None):
        return {"message": "song not found"}, 404
    result = db.songs.delete_one({"id": song_data["id"]})
    if result and (result.deleted_count == 0):
        return {"message": "song not found"}, 404
    elif result and (result.deleted_count == 1):
        return "", 204
    return {"message":"song found, but nothing updated"}, 200
