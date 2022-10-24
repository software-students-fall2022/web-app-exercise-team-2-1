#!/usr/bin/env python3

from email import message
from flask import Flask, render_template, request, redirect, url_for, make_response
from dotenv import dotenv_values
from werkzeug.utils import secure_filename

import pymongo
import datetime
from bson.objectid import ObjectId
import sys, os

# modules useful for user authentication
import flask_login
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

# instantiate the app
app = Flask(__name__)
app.secret_key = 'team2'  

# set up flask-login for user authentication
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


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

except Exception as e:
    # the ping command failed, so the connection is not available.
    # render_template('error.html', error=e) # render the edit template
    print(' *', "Failed to connect to MongoDB at", config['MONGO_URI'])
    print('Database connection error:', e) # debug

# a class to represent a user
class User(flask_login.UserMixin):
    # inheriting from the UserMixin class gives this blank class default implementations of the necessary methods that flask-login requires all User objects to have
    # see some discussion of this here: https://stackoverflow.com/questions/63231163/what-is-the-usermixin-in-flask
    def __init__(self, data):
        '''
        Constructor for User objects
        @param data: a dictionary containing the user's data pulled from the database
        '''
        self.id = data['_id'] # shortcut to the _id field
        self.data = data # all user data from the database is stored within the data field



def locate_user(user_id=None, username=None):
    '''
    Return a User object for the user with the given id or email address, or None if no such user exists.
    @param user_id: the user_id of the user to locate
    @param email: the email address of the user to locate
    '''
    if user_id:
        # loop up by user_id
        criteria = {"_id": ObjectId(user_id)}
    else:
        # loop up by email
        criteria = {"username": username}
    doc = db.users.find_one(criteria) # find a user with this email

    # if user exists in the database, create a User object and return it
    if doc:
        # return a user object representing this user
        user = User(doc)
        return user
    # else
    return None
    
if locate_user(username = "moderator"):
    hash_pass = generate_password_hash("moderator")
    mod_id = db.users.insert_one({"username": "moderator", "password": hash_pass, "is_moderator": True}).inserted_id 
@login_manager.user_loader
def user_loader(user_id):
    ''' 
    This function is called automatically by flask-login with every request the browser makes to the server.
    If there is an existing session, meaning the user has already logged in, then this function will return the logged-in user's data as a User object.
    @param user_id: the user_id of the user to load
    @return a User object if the user is logged-in, otherwise None
    '''
    return locate_user(user_id=user_id) # return a User object if a user with this user_id exists


# set up any context processors
# context processors allow us to make selected variables or functions available from within all templates

@app.context_processor
def inject_user():
    # make the currently-logged-in user, if any, available to all templates as 'user'
    return dict(user=flask_login.current_user)


moderator_mode = False

valid_locations = {'On campus', 'Off campus'}
valid_types = {'Academic building', 'Cafe/Restaurant', 'Library', 'Non-restaurant store', 'Miscellaneous'}
valid_noise_levels = {'Silent', 'Quiet', 'Conversational', 'Loud'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = os.path.join('static', 'images', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# set up the routes
@app.route('/')
def authenticate():
    #Route for the home page
    return render_template("moderator_login.html", message = "Please login or sign up!")

@app.route('/home')
def home():
    docs = db.spots.find({}).sort("created_at", -1)
    current_user = flask_login.current_user
    if current_user.data["is_moderator"]:
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
@flask_login.login_required
def moderator_home():
    #Route for the moderator home page
    docs = db.spots.find({}).sort("created_at", -1) 
    return render_template('moderator_home.html', docs = docs, title='Moderator Home')  # render the home template

@app.route('/moderator_home', methods = ['POST'])
@flask_login.login_required
def delete_spot():
    spotId = request.form['SpotId']
    db.spots.delete_one({"_id": ObjectId(spotId)})
    return redirect(url_for('moderator_home')) # render the home template


@app.route('/moderator_detail')
@flask_login.login_required
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
    
    return render_template('detail_moderator.html', doc = doc, purchase = purchase, reviews = reviews, reviewStar = reviewStar, spotStar = spotStar, title=doc["name"]) 

@app.route('/moderator_detail', methods = ['POST'])
@flask_login.login_required
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
@flask_login.login_required
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
    
    return render_template('detail.html', doc = doc, purchase = purchase, reviews = reviews, reviewStar = reviewStar, spotStar = spotStar, title = doc["name"]) 

@app.route('/detail/like', methods = ['POST'])
@flask_login.login_required
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
@flask_login.login_required
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
        "user": flask_login.current_user.data["username"]
        }
        db.reviews.insert_one(review)
        reviewTemp = db.reviews.find_one({"star" : star, "text" : reviewText,"spot" : spotId})
        reviewId = reviewTemp["_id"]
        spot = db.spots.find_one({"_id": ObjectId(spotId)})
        newStar = (spot["star"] * len(spot["reviewId"]) + int(star))/(len(spot["reviewId"]) + 1)
        db.spots.update_one({"_id": ObjectId(spotId)}, {'$push': {'reviewId': reviewId}, '$set':{ 'star': newStar}})
    
    return redirect(url_for('detail', SpotId = spotId))


@app.route('/create')
@flask_login.login_required
def create_post():
    # Route for the add study spot page
    return render_template('add_spot.html', title='Create Study Spot')  # render the add study spot template


# route to handle adding new spots to the database
# route accepts form submission and adds a document to database
@app.route('/create', methods = ['POST'])
@flask_login.login_required
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
        return render_template('add_spot.html', title="Create Study Spot") # TODO: display error msgs

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
        "added_by": flask_login.current_user.data["username"],
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
@flask_login.login_required
def edit_s(mongoid):
    # Route for the add study spot page
    doc = db.spots.find_one({"_id": ObjectId(mongoid)})
    return render_template('edit_spot.html', mongoid=mongoid, doc=doc, title="Edit Spot")

@app.route('/edit/<mongoid>', methods = ['POST'])
@flask_login.login_required
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

# @app.route('/moderator_login')
# def moderator_login():

#     # Route for the moderator login page
#     return render_template('moderator_login.html') 

# @app.route('/moderator_login', methods =['POST'])
# def moderator_authenticate():
#     username = request.form['fusername']
#     password = request.form['fpassword']

#     docs = db.moderators.find()
#     for doc in docs: 
#         if username == doc["username"] and password == doc["password"]:
#             global moderator_mode 
#             moderator_mode = True
#             return home()

#     return render_template('moderator_login.html') 




@app.route('/search')
@flask_login.login_required
def search():
    # Route for the moderator login page
    return render_template('search_page.html', title="Search") 

# route handling requests to search for specific study spots
@app.route('/search', methods = ['POST'])
@flask_login.login_required
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
    
    if location != "":
        query["location"] = location
    else:
        query["location"] = {"$exists": True}

    if type != "":
        query["type"] = type
    else:
        query["type"] = {"$exists": True}
    
    if purchase_info != "":
        query["purchase_info"] = purchase_info
    else:
        query["purchase_info"] = {"$exists": True}
    
    if noise_level != "":
        query["noise_level"] = noise_level
    else:
        query["noise_level"] = {"$exists": True}

    docs = db.spots.find(query).sort("created_at", -1)
    print(query)

    
    return render_template("home.html", docs = docs) # pass the list of search results as an argument to the home page for displaying 


# route to handle the submission of the login form
@app.route('/signup', methods=['POST'])
def signup_submit():
    # grab the data from the form submission
    username = request.form['fusername']
    password = request.form['fpassword']
    hashed_password = generate_password_hash(password) # generate a hashed password to store - don't store the original
    
    # check whether an account with this email already exists... don't allow duplicates
    if locate_user(username = username):
        # flash('An account for {} already exists.  Please log in.'.format(username))
        return render_template("moderator_login.html", message = "This username already exists.")

    # create a new document in the database for this new user
    user_id = db.users.insert_one({"username": username, "password": hashed_password, "is_moderator": False}).inserted_id # hash the password and save it to the database
    if user_id:
        # successfully created a new user... make a nice user object
        user = User({
            "_id": user_id,     
            "username": username,
            "password": hashed_password,
            "is_moderator": False
        })
        flask_login.login_user(user) # log in the user using flask-login
        # flash('Thanks for joining, {}!'.format(user.data['username'])) # flash can be used to pass a special message to the template we are about to render
        return redirect(url_for('home'))
    # else
    return 'Signup failed'

# route to handle the submission of the login form
@app.route('/login', methods=['POST'])
def login_submit():
    username = request.form['fusername']
    password = request.form['fpassword']
    user = locate_user(username=username) # load up any existing user with this email address from the database
    # check whether the password the user entered matches the hashed password in the database
    if user and check_password_hash(user.data['password'], password):
        flask_login.login_user(user) # log in the user using flask-login
        # flash('Welcome back, {}!'.format(user.data['email'])) # flash can be used to pass a special message to the template we are about to render

        return redirect(url_for('home'))
    
    return render_template("moderator_login.html", message = "Incorrect Username or Password or Account Does Not Exist.")

# route to logout a user
@app.route('/logout')
def logout():
    flask_login.logout_user()
    # flash('You have been logged out.  Bye bye!') # pass a special message to the template
    return redirect(url_for('authenticate')) # re
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
