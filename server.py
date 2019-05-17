from flask import Flask, render_template, redirect, request, session, flash, json
from mysqlconnection import connectToMySQL
from google.cloud import vision
from google.cloud.vision import types

app = Flask(__name__)
app.secret_key = 'Galadriel'

from flask_bcrypt import Bcrypt
bcrypt = Bcrypt(app)

import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PASSWORD_REGEX = re.compile(r'^(?=^.{8,}$)(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?!.*\s)[0-9a-zA-Z!@#$%^&*()]*$')

SCHEMA = "login_reg"

@app.route('/')
def index():
    mysql = connectToMySQL(SCHEMA)
    users = mysql.query_db("SELECT * FROM users;")
    print(users)
    # if 'user_id' in session:
    #     return redirect('/success')
    return render_template("index.html", all_users = users)

@app.route('/success')
def success():
    if 'user_id' not in session:
        return redirect('/')
    user_id = session['user_id']
    mysql = connectToMySQL(SCHEMA)
    query = "SELECT * FROM users WHERE id = %(id)s;"
    data = { "id" : session['user_id'] }
    user = mysql.query_db(query, data)
    print(user)
    
    return render_template("success.html", users = user)


@app.route('/users/create', methods =  ["POST"])
def userRegistration():
    is_valid = True
    if len(request.form["first_name"]) < 1:
        is_valid = False
        flash("Please enter a first name")
    if len(request.form["last_name"]) < 1:
        is_valid = False
        flash("Please enter a last name")
    if not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid email address!")
        is_valid = False
    if not PASSWORD_REGEX.match(request.form['password']):
        flash("Invalid Password: Must contain at least 8 characters, upper case letter, lower case letter, and a number.")
        is_valid = False
    if request.form["confirm_password"] != request.form["password"]:
        is_valid = False
    
    mysql = connectToMySQL(SCHEMA)
    validate_email_query = "SELECT id FROM users WHERE email=%(email)s"
    form_data = {
        'email': request.form['email']
    }
    existing_users = mysql.query_db(validate_email_query, form_data)

    if len(existing_users) > 0:
        flash("Email already in use")
        is_valid = False

    if is_valid != True:
        return redirect('/')
    if is_valid:
        pw_hash = bcrypt.generate_password_hash(request.form['password']) 
        print(pw_hash)
        mysql = connectToMySQL(SCHEMA)
        create_query = "INSERT INTO users (first_name, last_name, email, pw_hash, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW());"
        create_data = {
            "fn": request.form['first_name'],
            "ln": request.form['last_name'],
            "em": request.form['email'],
            "pw": pw_hash
        }
        user_id = mysql.query_db(create_query, create_data)
        session['user_id']= user_id
        return redirect("/success")


@app.route('/login', methods=['POST'])
def login():
    mysql = connectToMySQL(SCHEMA)
    query = "SELECT * FROM users WHERE email = %(email)s;"
    data = { "email" : request.form["email"] }
    user_id = mysql.query_db(query, data)
    if user_id:
        if bcrypt.check_password_hash(user_id[0]['pw_hash'], request.form['password']):
            session['user_id'] = user_id[0]['id']
            return redirect('/success')

    flash("Username or Password incorrect")
    return redirect("/")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

@app.route("/showtext")
def showText():
    if 'user_id' not in session:
        return redirect('/')
    user_id = session['user_id']
    pic = session['pic']
    client = vision.ImageAnnotatorClient()
    image = vision.types.Image()
    image.source.image_uri = pic
    respText = client.text_detection(image=image)
    responseLab = client.label_detection(image=image)
    labels = responseLab.label_annotations
    responseFace = client.face_detection(image=image)
    faces = responseFace.face_annotations
    likelihood_name = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE','LIKELY', 'VERY_LIKELY')
    # print('Faces:')
    # print('\n'.join([d.description for d in respText.text_annotations]))
    return render_template("answer.html", pic= pic, descriptions = respText.text_annotations, faces = faces, likelihood_name= likelihood_name, labels = labels)

@app.route("/answer", methods=['POST'])
def answer():
    session['pic'] = request.form["pic"]
    return redirect("/showtext")



if __name__ == "__main__":
    app.run(debug=True)