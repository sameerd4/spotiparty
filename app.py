from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
from spotify_actions import req_auth, req_token, generate, create_party_playlist
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from whitenoise import WhiteNoise

'''

App Config

'''


app = Flask(__name__)
#app.secret_key = 'bruh'.encode('utf8')
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
#    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
#    party = relationship("Party", back_populates="users")


    def __init__(self, user_id, playlist_id, first_name, token, party_id):
        self.spotify_id = user_id
        self.playlist_id = playlist_id
        self.first_name = first_name
        self.auth_token = token
        self.party_id = party_id

    def __repr__(self):
        return '<User %r>' % self.spotify_id
'''
class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(40), unique=True, nullable=False)
    users = relationship("User", back_populates="party")

    def __init__(self, id, playlist_id):
        self.spotify_id = usr_id
        self.playlist_id = playlist_id

'''
db.create_all()

def get_members(party_id):
    return User.query.filter_by(party_id=party_id)


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

        party_info = create_party_playlist(session.get('token'), pl_name, pl_desc)

        host_first_name = str(party_info[0])
        host_spotify_id = str(party_info[1])
        party_playlist_id = str(party_info[2])

        # Store playlist ID in session
        session['party_playlist_id'] = party_playlist_id

        found_user = User.query.filter_by(spotify_id=host_spotify_id).first()

        if found_user:
            found_user.auth_token = session.get('token')
            found_user.party_id = party_id
            found_user.playlist_id = party_playlist_id
            db.session.commit()

        else:
            user = User(host_spotify_id, party_playlist_id, host_first_name, session.get('token'), party_id)
            db.session.add(user)
            db.session.commit()

        return redirect(url_for('lobby'))



@app.route('/lobby', methods=['GET', 'POST'])
def lobby():
    return render_template('lobby.html', party_id=session['party_id'], party_members = get_members(session['party_id']))

@app.route('/start_party', methods=['GET', 'POST'])
def start_party():

    members = get_members(session['party_id'])

    guest_tokens = [member.auth_token for member in members]

    generate(guest_tokens[0], guest_tokens, session['party_playlist_id'])

    return render_template('party.html', playlist_id=session['party_playlist_id'], party_id=session['party_id'], party_members = get_members(session['party_id']))


'''

@app.route('/join_party', methods=['GET', 'POST'])
def join_party():

    if request.method == 'POST':

        # TO DO: get custom playlist name and description from jquery post request
        pl_name = session.get('pl_name')
        pl_desc = session.get('pl_desc')

        # Generate random 4-digit party ID
        # TO DO: check that it's unique in the database
        import random
        party_id = random.randint(1000,9999)

        # Store party ID in session
        session['party_id'] = party_id

        token = session.get('token')

        found_user = User.query.filter_by(spotify_id=user_spotify_id).first()

        if found_user:
            found_user.playlist_id = user_playlist_id
            db.session.commit()

        else:
            user = User(user_spotify_id, user_playlist_id, user_first_name, token)
            db.session.add(user)
            db.session.commit()

        return redirect(url_for('success'))

    else:




'''
# Generate playlist view


@app.route('/generate_playlist', methods=['GET', 'POST'])
def generate_playlist():

    if request.method == 'POST':

        # TO DO: get custom playlist name and description from jquery post request
        pl_name = session.get('pl_name')
        pl_desc = session.get('pl_desc')



        # Using token from Flask session, generate playlist
        token = session.get('token')
        user_info = generate(token, pl_name, pl_desc)

        user_first_name = str(user_info[0])
        user_spotify_id = str(user_info[1])
        user_playlist_id = str(user_info[2])

        # Store playlist ID in session
        session['user_pl_id'] = user_playlist_id

        found_user = User.query.filter_by(spotify_id=user_spotify_id).first()

        if found_user:
            found_user.playlist_id = user_playlist_id
            db.session.commit()

        else:
            user = User(user_spotify_id, user_playlist_id, user_first_name, token)
            db.session.add(user)
            db.session.commit()

        return redirect(url_for('success'))

    else:
        if session.get('token'):
            session.pop('pl_name', None)
            session.pop('pl_desc', None)

            # Load playlist generator page
            return render_template('generate_playlist.html', title='generate playlist')
        else:

            # Return home if user attempts to access page without going through
            # proper authorization
            return redirect(url_for('home'))


# Update modal form (backend page)


@app.route('/update', methods=["GET", "POST"])
def update():

    if request.method == 'POST':

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
