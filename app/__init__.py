from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from flask_bootstrap import Bootstrap
from flask_moment import Moment

app = Flask(__name__, template_folder='./templates', static_folder='./static')
app.config.from_object(Config)
db = SQLAlchemy(app)
login = LoginManager(app)
bootstrap = Bootstrap(app)
moment = Moment(app)


# define view for logging in
login.login_view = 'login'
from app import routes, models
