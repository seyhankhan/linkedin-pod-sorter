############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
############ github.com/seyhanvankhan


################################ IMPORT MODULES ################################


from flask import Flask, render_template, redirect, request, session, url_for
from models import db, User
from passlib.hash import sha256_crypt
import importlib


################################### INIT APP ###################################


app = Flask(__name__)

# if importlib.util.find_spec('flask_heroku'):
# 	from flask_heroku import Heroku
# 	heroku = Heroku(app)
# else:
# 	app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/linkedinPodSorter'
#
# db.init_app(app)
# app.secret_key = "s14a"


##################################### INDEX ####################################


@app.route('/')
def index():
	return render_template('index.html', title='Home')


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
    app.run(debug=True)
