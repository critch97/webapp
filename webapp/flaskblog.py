from flask import Flask, render_template, url_for, flash, redirect, request, session
from forms import RegistrationForm, LoginForm
import pymysql
from flask_bcrypt import Bcrypt
import secrets
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from PIL import Image
# Using static_folder to allow me to upload pictures
app = Flask(__name__, static_folder="static", static_url_path="")
app.config["SECRET_KEY"] = ""
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
bcrypt = Bcrypt(app)

temp_ip = ''# AWS RDS MariaDB
db_user = "" # db username
db_password = ""# db password


# Setting routes for the URLs
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html", title = "About")

@app.route("/register", methods=["POST","GET"])
def register():
    # If the user is already logged in, redirects to the profile page
    # Updated layout.html to only show register whilst not logged in
    if "loggedin" in session:
        flash("Account is already logged in", "danger")
        return redirect(url_for("profile"))
    form = RegistrationForm()
    # If all of the information in RegistrationForm(FlaskForm) (forms.py) is submitted
    if form.validate_on_submit():
        if request.method=="POST":
            username= form.username.data
            email = form.email.data
            default_pic = "default.jpg"
            # profile_picture = "default.jpg"
            # Password hashing for security
            hash_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

            # Connecting to the sql database
            connection = pymysql.connect(host=temp_ip, user=db_user, password=db_password, db=db_name , port=3306)
            try:
                with connection.cursor() as cursor:
                    # Testing to see if the user already exists
                    test = cursor.execute('SELECT * FROM accounts WHERE username=%s or email=%s',(username, email))
                    connection.close()

                    if test:
                        flash(f"Login/Username is already registered on this website", "danger")

                    else:
                        # Connecting to the sql database
                        connection = pymysql.connect(host=temp_ip,user=db_user, password=db_password, db=db_name, port=3306)
                        with connection.cursor() as cursor:
                            cursor.execute("""INSERT INTO accounts (username,password,email,profile_pictures) VALUES(%s,%s,%s,%s)""", (username, hash_password, email, default_pic))
                            connection.commit()
                            flash(f"Congratulations {form.username.data}, your account has been created!", "success")
                            login()
                            return redirect(url_for("profile"))

            finally:
                pass

    return render_template("register.html", title = "Register", form = form)


@app.route("/login", methods=["POST","GET"])
def login():
    # If the user is already logged in, redirects to the profile page
    if "loggedin" in session:
        flash("Account is already logged in", "danger")
        return redirect(url_for("profile"))

    form = LoginForm()
    if form.validate_on_submit():
        if request.method=="POST":
            # Email and password entered by the user on the login page
            email = form.email.data
            password_auth = form.password.data
            # Connecting to the sql database
            connection = pymysql.connect(host=temp_ip, user=db_user, password=db_password, db=db_name, port=3306)
            try:
                with connection.cursor() as cursor:
                    # Testing to see if the user already exists
                    test = cursor.execute('SELECT email, password, id, username, profile_pictures FROM accounts WHERE email=%s',(email))
                    results = cursor.fetchall()
                    connection.close()

                    if test:
                        # If the user exists, the hashed_password is equal to the 3rd column in the SQL table (passwords)
                        # [0][1] because of the order that the data was SELECTED (email(0), password(1), id(2))
                        hashed_password = results[0][1]
                        # If the hashed password matches the entered password, login successful
                        if bcrypt.check_password_hash(hashed_password, password_auth) == True:
                            flash(f"Login Successful", "success")
                            # Creating a unique session id for the user (contained in a dictonary)
                            session["loggedin"] = True
                            session["id"] = results[0][2]
                            session["email"] = results[0][0]
                            session["username"] = results[0][3]
                            session["profile_pictures"] = results[0][4]

                            return redirect(url_for("profile"))
                        else:
                            flash(f"Invalid email/password combination", ("danger"))

                    else:
                        flash(f"Invalid email/password combination", ("danger"))
            finally:
                pass
    return render_template('login.html', title='Login', form=form)





@app.route("/upload_image", methods=["POST","GET"])
def upload_image():
    if request.method == "POST":
        if request.files:
            # Image chosen by the user
            image = request.files["image"]
            filename = secure_filename(image.filename)
            # Dropping the file name and only retaining the file extension (e.g. .jpg)
            _, file_extension = os.path.splitext(filename)

            # If the file is empty or the file type isn't supported, don't allow
            if image.filename == '' or file_extension.lower() not in [".jpg",".png", ".jpeg"]:
                flash("Must upload an suiteable image extension (.jpg or .png)","danger")
                return redirect(url_for("upload_image"))
            # Creating a random file name
            random_hex = secrets.token_hex(8)
            pic_filename = random_hex + file_extension
            # Choosing the path to save the new profile picture
            pic_path = os.path.join(app.root_path, 'static/profile_pics',pic_filename)
            # Choosing the output size of the image
            output_size = (125,125)
            i = Image.open(image)
            i.thumbnail(output_size)
            # Saving the image in the folder specified in pic_path rootpath/static/profile_pics
            i.save(pic_path)

            connection = pymysql.connect(host=temp_ip, user=db_user, password=db_password, db=db_name, port=3306)
            with connection.cursor() as cursor:
                id_pic = session.get("id")
                # Storing the filename of the image in the database, identified by id
                cursor.execute('update accounts set profile_pictures=%s where id=%s', (pic_filename, id_pic))
                connection.commit()
                connection.close()
                flash('Updated profile picture','success')
                image_file = url_for('static', filename='profile_pics/' + str(session.get("profile_picture")))

            return redirect(url_for("profile"))

    return render_template("upload_image.html", title="upload image")


@app.route("/profile", methods=["POST","GET"])
def profile():
    if "loggedin" in session:
        connection = pymysql.connect(host=temp_ip, user=db_user, password=db_password, db=db_name, port=3306)
        with connection.cursor() as cursor:
            cursor.execute('SELECT profile_pictures FROM accounts WHERE id=%s',(session.get('id')))
            results = cursor.fetchall()
            picture_file = results[0][0]
            connection.close()
            if results:
                # Checks to see if the user is already signed in by searching the dictonary values for "loggedin" ("loggedin":True)
                # Updated layout.html to not show this unless logged in
                image_file = url_for('static', filename='profile_pics/' + str(picture_file))
                return render_template("profile.html",image_file=image_file)
            else:
                image_file = url_for('static', filename='profile_pics/' + 'default.jpg')
                return render_template("profile.html",image_file=image_file)

    # Else if the user doesn't have a 'loggedin' value (not signed in), then it redirects to the sign in page
    flash(f"Please log in to view the profile page", "danger")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # Deletes all of the session data, signing the user out.
    session.pop("loggedin",None)
    session.pop("id",None)
    session.pop("username",None)
    session.pop("email", None)
    return redirect(url_for("login"))



if __name__=="__main__":
    app.run(port=80, host=0.0.0.0)
