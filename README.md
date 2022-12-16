[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-c66648af7eb3fe8bc4f294546bfd86ef473780cde1dea487d3c4ff354943c9ae.svg)](https://classroom.github.com/online_ide?assignment_repo_id=8874489&assignment_repo_type=AssignmentRepo)
# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

A mobile web application for NYU students to view, rate, and review study spots on the various NYU campus buildings.

## User stories

View all user stories [here](https://github.com/software-students-fall2022/web-app-exercise-team-2-1/issues).

## Task boards

View task boards [here](https://github.com/software-students-fall2022/web-app-exercise-team-2-1/projects?query=is%3Aopen).

## Members

Charlie Xiang [Github](https://github.com/xiang-charlie)
Michael Ma [Github](https://github.com/mma01us)
Robert Chen [Github](https://github.com/RobertChenYF)
Sarah Al-Towaity [Github](https://github.com/sarah-altowaity1)

## Instructions to Run the App

### Build and launch the database

- install and run [docker desktop](https://www.docker.com/get-started)
- create a [dockerhub](https://hub.docker.com/signup) account
- run command, `docker run --name mongodb_dockerhub -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secret -d mongo:latest`

The back-end code will integrate with this database. However, it may be occasionally useful interact with the database directly from the command line:

- connect to the database server from the command line: `docker exec -ti mongodb_dockerhub mongosh -u admin -p secret`
- show the available databases: `show dbs`
- select the database used by this app: `use example`
- show the documents stored in the `messages` collection: `db.messages.find()` - this will be empty at first, but will later be populated by the app.
- exit the database shell whenever you have had your fill: `exit`

If you have trouble running Docker on your computer, use a database hosted on [MongoDB Atlas](https://www.mongodb.com/atlas) instead. Atlas is a "cloud" MongoDB database service with a free option. Create a database there, and make note of the connection string, username, password, etc.

### Create a `.env` file

A file named `.env` is necessary to run the application. This file contains sensitive environment variables holding credentials such as the database connection string, username, password, etc. This file should be excluded from version control in the `[.gitignore](.gitignore)` file.

Copy the into a file named `.env` and edit the values to match your database. If following the instructions and using Docker to run the database, the values should be:

```
MONGO_DBNAME=example
MONGO_URI="mongodb://admin:secret@localhost:27017/example?authSource=admin&retryWrites=true&w=majority"
```

The other values can be left alone.

### Set up a Python virtual environment

This command creates a new virtual environment with the name `.venv`:

```bash
python3 -m venv .venv
```

### Activate the virtual environment

To activate the virtual environment named `.venv`...

On Mac:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate.bat
```

### Install dependencies into the virtual environment

The file named, `requirements.txt` contains a list of dependencies - other Python modules that this app depends upon to run.

To install the dependencies into the currently-active virtual environment, use `pip`, the default Python "package manager" - software that takes care of installing the correct version of any module into your in the correct place for the current environment.

```bash
pip3 install -r requirements.txt
```

### Run the app
```bash
flask run
```

### Enter Credentials 
Upo loading up the mobile appilcation, a log in/sign up page will appear, prompting the user to enter a username and password. If the user is a moderator, inputting the string "moderator" for both the username and password should load up different screens with slightly different functionalities than those designed for regular users. Incorrect log in involves either the username or password being incorrect or the user not having signed up previously. In these cases, an error messasge will be displayed to notify the user of improper log in. Incorrect sign up involves an account already existing with that same username, upon which, again, a message will be displayed to the user. Upon successful sign up, you are directed to the home page with a listing of the study spots currently in the database. You can always log out by clicking on the log out button on the upper right corner of the page.

#### Moderator Pages
As a moderator, you will be able to delete study spots by clicking on the delete icon next to the study spot image. You can also edit the spot by clicking on the "Edit Spot" button and update the fields. You can also delete reviews when clicking on a specific study spot, loading up a special "moderator"-formatted screen to view the study spot listing and the reviews. As a moderator, you can also search spots and add spots, if desired.

#### Regualar User Page
As a general user, you can add study spot by clicking on the plus icon on the bottom bar, search spots, either by type or name, and add reviews to preexisting spots. You can also like/dislike other people's reviews. 
