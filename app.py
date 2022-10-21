#!/usr/bin/env python3

from crypt import methods
from flask import Flask, render_template, request, redirect, url_for, make_response
from dotenv import dotenv_values

import pymongo
import datetime
from bson.objectid import ObjectId
import sys

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
except Exception as e:
    # the ping command failed, so the connection is not available.
    # render_template('error.html', error=e) # render the edit template
    print(' *', "Failed to connect to MongoDB at", config['MONGO_URI'])
    print('Database connection error:', e) # debug


# set up the routes
@app.route('/')
def home():
    #Route for the home page
    docs = db.spots.find({}).sort("created_at", -1) 
    return render_template('home.html', docs = docs)  # render the home template

@app.route('/detail')
def detail():
    # Route for the detail page
    return render_template('detail.html')  # render the detail template

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

    db.spots.insert_one(doc) # insert a new document

    return redirect(url_for('home'))

@app.route('/moderator_login')
def moderator_login():

    # Route for the moderator login page
    return render_template('moderator_login.html') 

@app.route('/search')
def search():
    # Route for the moderator login page
    return render_template('search_page.html') 

# route handling requests to search for specific study spots
@app.route('/search', methods = ['POST'])
def search_spots():
    name = request.form['fspotname']
    type = request.form['ftype']
    if type == "---" and name != "":
        docs = db.spots.find({"name": name}).sort("created_at", -1) 
    else:
        if type != "---" and name == "":
            docs = db.spots.find({"type": type}).sort("created_at", -1)
        elif type != "---" and name != "":
            docs = db.spots.find({"name": name, "type": type}).sort("created_at", -1)
        else:
            docs = db.spots.find()
    return render_template("home.html", docs = docs) # pass the list of search results as an argument to the home page for displaying 

"""
# route to view the edit form for an existing post
@app.route('/edit/<mongoid>')
def edit(mongoid):
    
    #Route for GET requests to the edit page.
    #Displays a form users can fill out to edit an existing record.
    
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    return render_template('edit.html', mongoid=mongoid, doc=doc) # render the edit template


# route to accept the form submission to delete an existing post
@app.route('/edit/<mongoid>', methods=['POST'])
def edit_post(mongoid):
    
    #Route for POST requests to the edit page.
    #Accepts the form submission data for the specified document and updates the document in the database.
    
    name = request.form['fname']
    message = request.form['fmessage']

    doc = {
        # "_id": ObjectId(mongoid), 
        "name": name, 
        "message": message, 
        "created_at": datetime.datetime.utcnow()
    }

    db.exampleapp.update_one(
        {"_id": ObjectId(mongoid)}, # match criteria
        { "$set": doc }
    )

    return redirect(url_for('home')) # tell the browser to make a request for the / route (the home function)

# route to delete a specific post
@app.route('/delete/<mongoid>')
def delete(mongoid):
    
    #Route for GET requests to the delete page.
    #Deletes the specified record from the database, and then redirects the browser to the home page.
    
    db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
    return redirect(url_for('home')) # tell the web browser to make a request for the / route (the home function)


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
