#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, make_response
from dotenv import dotenv_values
from werkzeug.utils import secure_filename

import pymongo
import datetime
from bson.objectid import ObjectId
import sys, os

# instantiate the app
app = Flask(__name__)

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
config = dotenv_values(".env")

# turn on debugging if in development mode
if config['FLASK_ENV'] == 'development':
    # turn on debugging, if in development
    app.debug = True  # debug mnode


# connect to the database
cxn = pymongo.MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=5000, tlsAllowInvalidCertificates=True)
try:
    # verify the connection works by pinging the database
    cxn.admin.command('ping') # The ping command is cheap and does not require auth.
    db = cxn[config['MONGO_DBNAME']] # store a reference to the database
    print(' *', 'Connected to MongoDB!') # if we get here, the connection worked!
    if len(list(db.moderators.find())) == 0:
        db.moderators.insert_one({"username": "moderator", "password": "moderator"})
        db.moderators.insert_one({"username": "moderator", "password": "1234"})

except Exception as e:
    # the ping command failed, so the connection is not available.
    # render_template('error.html', error=e) # render the edit template
    print(' *', "Failed to connect to MongoDB at", config['MONGO_URI'])
    print('Database connection error:', e) # debug

moderator_mode = False

valid_locations = {'On campus', 'Off campus'}
valid_types = {'Academic building', 'Cafe/Restaurant', 'Library', 'Non-restaurant store', 'Miscellaneous'}
valid_noise_levels = {'Silent', 'Quiet', 'Conversational', 'Loud'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = os.path.join('static', 'images', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# set up the routes
@app.route('/')
def home():
    #Route for the home page
    docs = db.spots.find({}).sort("created_at", -1)
    if moderator_mode:
        return render_template('moderator_home.html', docs = docs) 
    return render_template('home.html', docs = docs)  # render the home template

def printStar(starRating):
    starRating = round(float(starRating))
    index = 0
    starStr = ""
    while(index<5):
        if index < starRating:
            starStr += "★"
        else:
            starStr += "✩"
        index += 1

    return starStr

@app.route('/moderator_home')
def moderator_home():
    #Route for the moderator home page
    docs = db.spots.find({}).sort("created_at", -1) 
    return render_template('moderator_home.html', docs = docs)  # render the home template

@app.route('/moderator_home', methods = ['POST'])
def delete_spot():
    spotId = request.form['SpotId']
    db.spots.delete_one({"_id": ObjectId(spotId)})
    return redirect(url_for('moderator_home')) # render the home template


@app.route('/moderator_detail')
def moderator_detail():
    # Route for the detail page
    SpotId = request.args.get('SpotId')
    doc = db.spots.find_one({"_id": ObjectId(SpotId)})

    purchase = doc["purchase_info"]
    reviewIds = doc["reviewId"]
    if purchase:
        purchase = "No Purchase Required"
    else:
        purchase = "Purchase Required"
    
    spotStar = printStar(doc["star"])
    reviewTemp = db.reviews.find({ "_id": { '$in': reviewIds }}).sort("like", -1)
    
    #.sort("star", -1).sort("created_at",-1).sort("like", -1)
    reviewStar = []
    for review in reviewTemp:
        reviewStar.append(printStar(review["star"]))
    
    reviews = db.reviews.find({ "_id": { '$in': reviewIds } }).sort("like", -1)
    
    return render_template('detail_moderator.html', doc = doc, purchase = purchase, reviews = reviews, reviewStar = reviewStar, spotStar = spotStar) 

@app.route('/moderator_detail', methods = ['POST'])
def delete_review():
    reviewId = request.form['reviewId']
    review = db.reviews.find_one({"_id": ObjectId(reviewId)})
    spot = db.spots.find_one({"_id": ObjectId(review["spot"])})

    # remove review id from this spot, recalculate star
    if len(spot["reviewId"]) -1 > 0:
        newStar = (spot["star"] * len(spot["reviewId"]) - float(review["star"]))/(len(spot["reviewId"])-1)
    else: 
        newStar = 0
    db.spots.update_one({"_id": ObjectId(review["spot"])}, {'$pull': {'reviewId': ObjectId(reviewId)}, '$set':{ 'star': newStar}})
    db.reviews.delete_one({"_id": ObjectId(reviewId)})
    return redirect(url_for('moderator_detail', SpotId = spot["_id"])) # render the home template

@app.route('/detail')
def detail():
    # Route for the detail page
    SpotId = request.args.get('SpotId')
    doc = db.spots.find_one({"_id": ObjectId(SpotId)})

    purchase = doc["purchase_info"]
    reviewIds = doc["reviewId"]
    if purchase:
        purchase = "No Purchase Required"
    else:
        purchase = "Purchase Required"
    
    spotStar = printStar(doc["star"])
    reviewTemp = db.reviews.find({ "_id": { '$in': reviewIds }}).sort("like", -1)
    
    #.sort("star", -1).sort("created_at",-1).sort("like", -1)
    reviewStar = []
    for review in reviewTemp:
        reviewStar.append(printStar(review["star"]))
    
    reviews = db.reviews.find({ "_id": { '$in': reviewIds } }).sort("like", -1)
    
    return render_template('detail.html', doc = doc, purchase = purchase, reviews = reviews, reviewStar = reviewStar, spotStar = spotStar) 

@app.route('/detail/like', methods = ['POST'])
def like_review():

    reviewId  = request.form['reviewId']
    like = request.form['like']
    addlike = 0
    addDislike = 0
    if like == "like":
        addlike = 1
    elif like == "dislike":
        addDislike = 1
    review = db.reviews.find_one({"_id": ObjectId(reviewId)})
    db.reviews.update_one({"_id": ObjectId(reviewId)}, { '$inc': { "like": addlike, "dislike": addDislike}})
    return redirect(url_for('detail', SpotId = review["spot"]))

@app.route('/detail/post', methods = ['POST'])
def post_review():

    spotId  = request.form['SpotId']
    star = request.form['star']
    reviewText = request.form['reviewText']
    if len(reviewText) > 0:
        review = {
        "star" : star,
        "text" : reviewText,
        "spot" : spotId,
        "like" : 0,
        "dislike" : 0,
        "created_at": datetime.datetime.utcnow(),
        }
        db.reviews.insert_one(review)
        reviewTemp = db.reviews.find_one({"star" : star, "text" : reviewText,"spot" : spotId})
        reviewId = reviewTemp["_id"]
        spot = db.spots.find_one({"_id": ObjectId(spotId)})
        newStar = (spot["star"] * len(spot["reviewId"]) + int(star))/(len(spot["reviewId"]) + 1)
        db.spots.update_one({"_id": ObjectId(spotId)}, {'$push': {'reviewId': reviewId}, '$set':{ 'star': newStar}})
    
    return redirect(url_for('detail', SpotId = spotId))


@app.route('/create')
def create_post():
    # Route for the add study spot page
    
    return render_template('add_spot.html')  # render the add study spot template

# route to handle adding new spots to the database
# route accepts form submission and adds a document to database
@app.route('/create', methods = ['POST'])
def add_spot():
    name = request.form['fitem']
    address = request.form['faddress']
    location = request.form['flocation']
    type = request.form['ftype']
    purchase_info = False
    if request.form['fpurchase'] == 'Yes':
        purchase_info = True
    noise_level = request.form['fnoise']
    description = request.form['fdescription']
    filename = '' # optional image none by default

    # validate input (could be a function)
    invalid = False
    if name == '':
        invalid = True
    if address == '':
        invalid = True
    if location not in valid_locations:
        invalid = True
    if type not in valid_types:
        invalid = True
    if noise_level not in valid_noise_levels:
        invalid = True 

    if invalid:
        return render_template('add_spot.html') # TODO: display error msgs

    # optional image
    if 'fimage' in request.files:
        file = request.files['fimage']
        fname = file.filename
        if fname != '' and '.' in fname \
            and fname.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(fname)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # create a new document with the data the user entered
    doc = {
        "name": name,
        "image": filename,
        "address": address, 
        "created_at": datetime.datetime.utcnow(),
        "location": location, 
        "type": type,
        "purchase_info": purchase_info,
        "noise_level": noise_level,
        "description": description,
        "reviewId": [],
        "star": 0,
    }

    db.spots.insert_one(doc) # insert a new document

    return redirect(url_for('home'))

@app.route('/edit/<mongoid>')
def edit_s(mongoid):
    # Route for the add study spot page
    doc = db.spots.find_one({"_id": ObjectId(mongoid)})
    return render_template('edit_spot.html', mongoid=mongoid, doc=doc)

@app.route('/edit/<mongoid>', methods = ['POST'])
def edit_spot(mongoid):

    name = request.form['fitem']
    address = request.form['faddress']
    location = request.form['flocation']
    type = request.form['ftype']
    purchase_info = False
    if request.form['fpurchase'] == 'Yes':
        purchase_info = True
    noise_level = request.form['fnoise']
    description = request.form['fdescription']

    # create a new document with the data the user entered
    doc = {
        "name": name,
        "address": address, 
        "created_at": datetime.datetime.utcnow(),
        "location": location, 
        "type": type,
        "purchase_info": purchase_info,
        "noise_level": noise_level,
        "description": description,
    }

    db.spots.update_one({"_id": ObjectId(mongoid)}, {"$set": doc})

    return redirect(url_for('home'))

@app.route('/moderator_login')
def moderator_login():

    # Route for the moderator login page
    return render_template('moderator_login.html') 

@app.route('/moderator_login', methods =['POST'])
def moderator_authenticate():
    username = request.form['fusername']
    password = request.form['fpassword']

    docs = db.moderators.find()
    for doc in docs: 
        if username == doc["username"] and password == doc["password"]:
            global moderator_mode 
            moderator_mode = True
            return home()

    return render_template('moderator_login.html') 



@app.route('/search')
def search():
    # Route for the moderator login page
    return render_template('search_page.html') 

# route handling requests to search for specific study spots
@app.route('/search', methods = ['POST'])
def search_spots():
    name = request.form['fspotname']
    location = request.form['flocation']
    type = request.form['ftype']
    purchase_info = False
    if request.form['fpurchase'] == 'Yes':
        purchase_info = True
    noise_level = request.form['fnoise']

    # if type == "---" and name != "":
    #     docs = db.spots.find({"name": name}).sort("created_at", -1) 
    # else:
    #     if type != "---" and name == "":
    #         docs = db.spots.find({"type": type}).sort("created_at", -1)
    #     elif type != "---" and name != "":
    #         docs = db.spots.find({"name": name, "type": type}).sort("created_at", -1)
    #     else:
    #         docs = db.spots.find()

    query = dict()

    if name != "":
        query["name"] = name
    else:
        query["name"] = {"$exists": True}
    
    if location != "" or location == "---":
        query["location"] = location
    else:
        query["location"] = {"$exists": True}

    if type != "" or type == "---":
        query["type"] = type
    else:
        query["type"] = {"$exists": True}
    
    if purchase_info != "" or purchase_info == "---":
        query["purchase_info"] = purchase_info
    else:
        query["purchase_info"] = {"$exists": True}
    
    if noise_level != "" or noise_level == "---":
        query["noise_level"] = noise_level
    else:
        query["noise_level"] = {"$exists": True}

    docs = db.spots.find(query).sort("created_at", -1)
    print(query)

    
    return render_template("home.html", docs = docs) # pass the list of search results as an argument to the home page for displaying 


"""
route to handle any errors

@app.errorhandler(Exception)
def handle_error(e):

    # Output any errors - good for debugging.

    return render_template('error.html', error=e)  # render the edit template
"""
# run the app
if __name__ == "__main__":
    #import logging
    # logging.basicConfig(filename='/home/ak8257/error.log',level=logging.DEBUG)
    app.run(debug=True)
