from flask import Flask, request, render_template, redirect,url_for,session,flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timedelta
import re

app=Flask(__name__)
app.secret_key="rjdk8741tao"
url="mongodb://localhost:27017/"

client=MongoClient(url)
db=client.flask_wtf_login
users=db.users
items_menu=db.items
bills=db.bills

def is_password_storng(Password):
    if len(Password) < 8:
        return False
    if not re.search(r"[a-z]", Password) or not re.search(r"[A-Z]", Password) or not re.search(r"\d", Password):
        return False
    if not re.search(r"[!@#$%^&*()-+{}|\"<>]?", Password):
        return False
    return True

@app.route('/')
def home():
    return render_template("form.html")

class user:
    def __init__(self,id,username, password):
        self.id=id
        self.username=username
        self.password=password

class signup(FlaskForm):
    username=StringField("username",validators=[InputRequired(),Length(min=4,max=15)])
    password=PasswordField("password",validators=[InputRequired(),Length(min=8,max=15)])
    submit=SubmitField("Signup")
class LoginForm(FlaskForm):
    username=StringField("username",validators=[InputRequired(),Length(min=4,max=15)])
    password=PasswordField("password",validators=[InputRequired(),Length(min=8,max=15)])
    submit=SubmitField("Login")

@app.route("/signin",methods=["GET","POST"])
def signin():
    form=signup()
    if form.validate_on_submit():
        name = form.username.data
        password = form.password.data
        hashed_pass=generate_password_hash(password)
        if not is_password_storng(password):
            flash("Password must be atleast 8 letters long,a-z,A-Z,0-9,Symbols ",'danger')
            return redirect(url_for('signin'))

        data = users.find_one({"name":name})
        if data:
            flash("User Name taken :(","danger")
            return render_template("signin.html",form=form)
        dic = {
            "name": name, "pass": hashed_pass
        }
        users.insert_one(dic)
        flash("Successfully Signed in","success")
        return redirect(url_for("login"))
    return render_template("signin.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        name = form.username.data
        password = form.password.data
        data = users.find_one({"name": name})
        if data:
            stored_hash_pass=data["pass"]
            if check_password_hash(stored_hash_pass,password):
                cur_user=user(id=str(data["_id"]),username=data["name"],password=data["pass"])
                session["user_id"]=cur_user.id
                flash("Successfully Logged in :)")
                return redirect(url_for("menu"))
            else:
                flash("Invalid Credentials","Danger")
        else:
            flash("User Not Found!","danger")
    return render_template("login.html",form=form)

@app.route("/logout")
def logout():
    session.pop("user_id",None)
    flash("Logged Out","Success")
    return redirect(url_for("home"))

def is_logged_in():
    return "user_id" in session

item={}
bill={"order":{}}
@app.route("/menu",methods=["GET","POST"])
def menu():
    if not is_logged_in():
        flash("Log in","Danger")
        return redirect(url_for("login"))
    item.update(items_menu.find_one({}))
    item.pop("_id",None)
    final_bill = []
    grand_total = 0
    if request.method=="POST":
        if "send" in request.form:
            quantities = {}
            for i in range(1,len(request.form)//2+1):
                dish=request.form.get(f"dish_{i}")
                quantity=int(request.form.get(f"quantity_{i}"))
                if quantity > 0:
                    if dish in quantities:
                        quantities[dish]+=quantity
                    else:
                        quantities[dish] = quantity
            for dish,quantity in quantities.items():
                if dish in bill["order"]:
                    bill["order"][dish]+=quantity
                else:
                    bill["order"][dish] = quantity

            for dish, quantity in bill["order"].items():
                if dish in item:
                    cost = int(item[dish] * quantity)
                    grand_total += cost
                    final = {"Dish": dish,
                                 "Quantity": quantity,
                                 "Cost": cost}
                    final_bill.append(final)
            final_tot = {"total": grand_total}
            final_bill.append(final_tot)
            return render_template("menu.html",items=item,bill=final_bill)
        elif "order" in request.form:
            for dish, quantity in bill["order"].items():
                if dish in item:
                    cost = int(item[dish] * quantity)
                    grand_total += cost
                    final = {"Dish": dish,
                             "Quantity": quantity,
                             "Cost": cost}
                    final_bill.append(final)
            final_tot = {"total": grand_total}
            final_bill.append(final_tot)
            session["final_bill"]=final_bill
            return redirect(url_for("show_bill",bill=final_bill))
    return render_template("menu.html",items=item,bill=[])

@app.route("/show_bill")
def show_bill():
    if not is_logged_in():
        flash("Log in","Danger")
        return redirect(url_for("login"))
    final_bill = session.get("final_bill", [])
    if final_bill:
        cur_user=session["user_id"]
        insert_bill={"user_id":cur_user,
                        "order_details":final_bill}
        bills.insert_one(insert_bill)
        return render_template("bill.html", bill=final_bill)
    if request.method=="POST":
        return render_template("menu.html")


@app.route("/history")
def history():
    if not is_logged_in():
        flash("Log in", "Danger")
        return redirect(url_for("login"))
    user=session.get("user_id")
    if request.method=="POST":
        return render_template("menu.html")
    data=bills.find({"user_id":user})
    data_list=list(data)
    bill_list=[]
    for bill in data_list:
        bill_list.append(bill["order_details"])
    return render_template("bills.html",bills=bill_list)


if __name__=="__main__":
    app.run(debug=True)