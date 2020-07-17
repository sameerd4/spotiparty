import os
import os.path
from os import path

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from whitenoise import WhiteNoise

from spotify_actions import (create_party_playlist, generate, get_user,
                             req_auth, req_token)

'''

App Config

'''


app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET')
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

# db config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_REDIRECT_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# database
db = SQLAlchemy(app)
db.app = app

class User(db.Model):
    spotify_id = db.Column(db.String(50), primary_key=True)
    playlist_id = db.Column(db.String(40), unique=False, nullable=False)
    first_name = db.Column(db.String(20), unique=False, nullable=True)
    auth_token = db.Column(db.String(20), unique=False, nullable=True)
    party_id = db.Column(db.Integer, unique=False, nullable=True)
    party_on = db.Column(db.BOOLEAN, unique=False, nullable=True)
#    host = db.Column(db.BOOLEAN, unique=False, nullable=True)
#    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
#    party = relationship("Party", back_populates="users")


    def __init__(self, user_id, playlist_id, first_name, token, party_id):
        self.spotify_id = user_id
        self.playlist_id = playlist_id
        self.first_name = first_name
        self.auth_token = token
        self.party_id = party_id
        self.party_on = False
#        self.host = host
#        self.party_on = False

    def __repr__(self):
        return '<User %r>' % self.spotify_id

db_file_name = os.environ.get('DB_REDIRECT_URI')
db_file_name = db_file_name[3 + db_file_name.index('/'):]
if not path.exists("db_file_name"):    
    db.create_all()

def get_members(party_id):
    return User.query.filter_by(party_id=party_id)


def get_parties():
    users = User.query.filter_by()
    return {user.party_id for user in users}

'''

Views

'''


# Home view
@app.route('/')
@app.route('/home')
def home():

    # Home page
    return render_template('home.html', title='Home')


# Login view


@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    # Redirect user to Spotify login page
    AUTH_FIRST = req_auth()
    return redirect(AUTH_FIRST)


# Callback view for Spotify API


@app.route('/callback')
def callback():
    if request.args.get('error') or not request.args.get('code'):

        # Prevents user from accessing page without going through authorization
        # steps properly
        return redirect(url_for('home'))
    else:
        # Get 'code' from Spotify request
        code = request.args.get('code')

        # Using 'code' provided by Spotify, request a user token from Spotify
        token = req_token(code)
        session['token'] = token

        return redirect(url_for('options'))

@app.route('/options')
def options():
    return render_template('options.html')


@app.route('/create_party', methods=['GET', 'POST'])
def create_party():

    if request.method == 'POST':
        return redirect(url_for('success')) 
    else:
        
        # TO DO: get custom playlist name and description from jquery post request
        pl_name = session.get('pl_name')
        pl_desc = session.get('pl_desc')

        # Generate random 4-digit party ID
        # TO DO: check that it's unique in the database
        import random
        party_id = random.randint(1000,9999)

        # Store party ID in session
        session['party_id'] = party_id

        session['host_status'] = True

        party_info = create_party_playlist(session.get('token'), pl_name, pl_desc)

        host_first_name = str(party_info[0])
        host_spotify_id = str(party_info[1])
        party_playlist_id = str(party_info[2])

        # Store playlist ID in session
        session['spotify_id'] = host_spotify_id
        session['party_playlist_id'] = party_playlist_id

        found_user = User.query.filter_by(spotify_id=host_spotify_id).first()

        if found_user:
            found_user.auth_token = session.get('token')
            found_user.party_id = party_id
            found_user.playlist_id = party_playlist_id
            found_user.party_on = False
#            found_user.host = True
            db.session.commit()

        else:
            user = User(host_spotify_id, party_playlist_id, host_first_name, session.get('token'), party_id)
            user.party_on = False
            db.session.add(user)
            db.session.commit()

        return redirect(url_for('lobby'))



@app.route('/lobby', methods=['GET', 'POST'])
def lobby():

    found_user = User.query.filter_by(spotify_id=session['spotify_id']).first()
    found_user.party_on = False
    db.session.commit()

    for party_member in get_members(session['party_id']):
        if party_member.party_on:
            found_user.party_on = True
            db.session.commit()
            return render_template('party.html', playlist_id=party_member.playlist_id, party_id=session['party_id'], party_members = get_members(session['party_id'])) 

    # Check if user is a host or not 
    return render_template('lobby.html', host=session['host_status'], party_id=session['party_id'], party_members = get_members(session['party_id']))

@app.route('/start_party', methods=['GET', 'POST'])
def start_party():

    members = get_members(session['party_id'])

    guest_tokens = [member.auth_token for member in members]

    generate(session['token'], guest_tokens, session['party_playlist_id'])

    user = User.query.filter_by(party_id=session['party_id']).first()
    user.party_on = True
    db.session.commit()


    return render_template('party.html', playlist_id=session['party_playlist_id'], party_id=session['party_id'], party_members = get_members(session['party_id']))




@app.route('/join_party', methods=['GET', 'POST'])
def join_party():

    if request.method == 'POST':

        # TO DO: get custom playlist name and description from jquery post request
        pl_name = session.get('pl_name')
        pl_desc = session.get('pl_desc')

        # Store party ID in session
        party_id = int(float(request.form.get('party_code')))
        session['party_id'] = party_id

        session['host_status'] = False
        token = session.get('token')

        spotify_info = get_user(token)

        user_first_name = str(spotify_info[0])
        user_spotify_id = str(spotify_info[1])
        profile_image = str(spotify_info[2]) #TO DO

        session['spotify_id'] = user_spotify_id

        found_user = User.query.filter_by(spotify_id=user_spotify_id).first()

        party_playlist_id = get_members(party_id)[0].playlist_id

        if found_user:
            found_user.party_id = party_id
            found_user.playlist_id = party_playlist_id
#            found_user.host = False
            db.session.commit()

        else:
            user = User(user_spotify_id, party_playlist_id, user_first_name, session.get('token'), party_id)
            db.session.add(user)
            db.session.commit()

        return redirect(url_for('lobby'))

    else:

        reg_ex = ""

        for id in get_parties():
            reg_ex += str(id)
            reg_ex += '|'
        
        reg_ex = reg_ex[:-1]

        return render_template('join_party.html', reg_ex=reg_ex)



# Update modal form (backend page)


@app.route('/update', methods=["GET", "POST"])
def update():

    if request.method == 'POST':
        #TODO
        # Get custom playlist name from jquery post
        pl_name = request.form.get('name')
        pl_desc = request.form.get('desc')

        # Store custom info into session
        session['pl_name'] = pl_name
        session['pl_desc'] = pl_desc

        return jsonify({'result': 'success'})

    if request.method == 'GET':
        return redirect(url_for('home'))


# Success landing page


@app.route('/success')
def success():

    if session.get('user_pl_id'):
        playlist_id = session.get('user_pl_id')
        return render_template('success.html', pl_id=playlist_id)
    else:
        return redirect(url_for('home'))


# Success landing page

'''
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')
'''

if __name__ == '__main__':
    app.run(debug=False)
