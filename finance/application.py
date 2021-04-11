import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    owned = db.execute("SELECT symbol, name, shares, price, price * shares AS total FROM owned WHERE userID=:userID", userID=session["user_id"])
    balance = getBalance()
    grandTotal = db.execute("SELECT SUM(price * shares) AS grandTotal FROM owned WHERE userID=:userID", userID=session["user_id"])[0]["grandTotal"]
    if not grandTotal:
        grandTotal = 0
    grandTotal += balance
    return render_template("index.html", owned=owned, balance=balance, grandTotal=grandTotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("Must enter a symbol")
        if not shares:
            return apology("Must enter number of shares")
        try:
            shares = int(shares)
        except:
            return apology("Must enter integer for number of shares")
        if shares < 1:
            return apology("Must enter positive number of shares")

        company = lookup(symbol)
        if company == None:
            return apology("invalid symbol", 400)
        balance = getBalance()
        #TODO check for enough money
        if (company["price"] * shares) > balance:
            return apology("You don't have enough money")
        db.execute("UPDATE users SET cash=:cash WHERE id=:userID", cash=balance-company["price"] * shares, userID=session["user_id"])
        db.execute("INSERT INTO owned (userID, symbol, name, shares, price) VALUES (:userID, :symbol, :name, :shares, :price)",
                    userID=session["user_id"], symbol=symbol, name=company["name"], shares=shares, price=company["price"])

        db.execute("INSERT INTO history (symbol, shares, price, transacted, userID) VALUES (:symbol, :shares, :price, :transacted, :userID)",
                    symbol=symbol, shares=shares, price=company["price"], transacted=datetime.datetime.now(), userID=session["user_id"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    table=db.execute("SELECT symbol, shares, price, transacted FROM history WHERE userID=:userID", userID=session["user_id"])
    return render_template("history.html", history=table)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        company=lookup(request.form.get("symbol"))
        if company == None:
            return apology("invalid symbol", 400)
        return render_template("quoted.html", company=company)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        if not username:
            return apology("must provide username", 400)

        elif not password:
            return apology("must provide password", 400)

        elif not confirm:
            return apology("must confirm password", 400)

        elif len(db.execute("SELECT username FROM users WHERE username=:username", username=username)) != 0:
            return apology("username already exists", 400)

        elif password != confirm:
            return apology("passwords do not match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashValue)", username=username, hashValue=generate_password_hash(password))

        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not shares:
            return apology("Must enter number of shares")
        try:
            shares = int(shares)
        except:
            return apology("Must enter integer for number of shares")
        if shares < 1:
            return apology("Must enter positive number of shares")

        if symbol == "Symbol":
            return apology("Please select a symbol")

        leftover = db.execute("SELECT shares FROM owned WHERE userID=:userID AND symbol=:symbol", userID=session["user_id"], symbol=symbol)[0]["shares"] - shares
        if leftover < 0:
            return apology("Not enough shares")

        company = lookup(symbol)

        db.execute("UPDATE users SET cash=:cash WHERE id=:userID", cash=getBalance() + company["price"] * shares, userID=session["user_id"])

        if leftover == 0:
            db.execute("DELETE FROM owned WHERE userID=:userID AND symbol=:symbol", userID=session["user_id"], symbol=symbol)
        else:
            db.execute("UPDATE owned SET shares=:shares WHERE userID=:userID AND symbol=:symbol", shares=leftover, userID=session["user_id"], symbol=symbol)

        db.execute("INSERT INTO history (symbol, shares, price, transacted, userID) VALUES (:symbol, :shares, :price, :transacted, :userID)",
                    symbol=symbol, shares=-shares, price=company["price"], transacted=datetime.datetime.now(), userID=session["user_id"])

        return redirect("/")
    else:
        symbols = db.execute("SELECT symbol FROM owned WHERE userID=:userID", userID=session["user_id"])
        return render_template("sell.html", symbols=symbols)


@app.route("/changePass", methods=["GET", "POST"])
@login_required
def changePass():
    if request.method == "POST":
        current = request.form.get("current")
        new = request.form.get("new")
        confirm = request.form.get("confirm")
        password = db.execute("SELECT hash FROM users WHERE id=:userID", userID=session["user_id"])[0]["hash"]

        if not current:
            return apology("must provide current password", 403)
        elif not new:
            return apology("must provide new password", 403)
        elif not confirm:
            return apology("must confirm new password", 403)
        elif not check_password_hash(password, current):
            return apology("current password must match")
        elif new != confirm:
            return apology("confirmed password must match")

        db.execute("UPDATE users SET hash=:password WHERE id=:userID", password=generate_password_hash(new), userID=session["user_id"])

        return redirect("/")
    else:
        return render_template("changePass.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

def getBalance():
    return db.execute("SELECT cash FROM users WHERE id=:userID", userID=session["user_id"])[0]["cash"]

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
