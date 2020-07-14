import sys
import os
import spotipy
import spotipy.util as util
import random
import string
import requests
from urllib.parse import quote
import base64
import json
import datetime

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get('REDIRECT_URI')

scope = 'user-top-read user-library-read playlist-modify-public'


def req_auth():

    show_dialog = "false"

    AUTH_FIRST_URL = f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={quote(redirect_uri)}&show_dialog={show_dialog}&scope={scope}'
    return AUTH_FIRST_URL


def req_token(code):

    # B64 encode variables
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())

    # Token data
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }

    # Token header
    token_header = {
        "Authorization": f"Basic {client_creds_b64.decode()}"
    }

    # Make request post for token info
    token_json = requests.post(
        'https://accounts.spotify.com/api/token', data=token_data, headers=token_header)

    # Checking if token is still valid, otherwise, refresh

    if "expires_in" in token_json.json():

        now = datetime.datetime.now()
        expires_in = token_json.json()['expires_in']
        expires = now + datetime.timedelta(seconds=expires_in)

        if now > expires:

            refresh_token_data = {
                "grant_type": "refresh_token",
                "refresh_token": token_json.json()['refresh_token']
            }

            refresh_token_json = requests.post(
                'https://accounts.spotify.com/api/token', data=refresh_token_data, headers=token_header)
            token = refresh_token_json.json()['access_token']

            return token
        else:
            token = token_json.json()['access_token']
            return token
    else:

        token = token_json.json()['access_token']

        return token


def generate(token, name, desc):

    spotifyObject = spotipy.Spotify(auth=token)

    user_id = str(spotifyObject.current_user()['id'])
    first_name = spotifyObject.current_user()['display_name'].split()[0]

    # Get user top artists
    user_top_artists = spotifyObject.current_user_top_artists(
        limit=5, time_range='medium_term')

    # Put top artists in dictionary
    artist_ids = []
    for artist in user_top_artists['items']:
        artist_ids.append(artist['id'])

    # Get list of recommended songs and put ID's in a list
    tracks = spotifyObject.recommendations(
        seed_artists=artist_ids, limit=50)
    track_ids = []
    for track in tracks['tracks']:
        track_ids.append(track['id'])

    # TO DO
    playlist_name = "Playlist for {}".format(first_name)
    playlist_desc = ""


    #TO DO
    if name:
        playlist_name = name

    if desc:
        playlist_desc = desc

    # create playlist and add to user library
    recommended_playlist = spotifyObject.user_playlist_create(
        user_id, playlist_name, description=playlist_desc)

    recommended_playlist_id = recommended_playlist['id']
    #add songs to playlist
    spotifyObject.user_playlist_add_tracks(
        user_id, recommended_playlist_id, track_ids)

    return [first_name, user_id, recommended_playlist_id]


def create_party_playlist(token, playlist_name, playlist_desc):
    spotifyObject = spotipy.Spotify(auth=token)
    user_id = str(spotifyObject.current_user()['id'])
    first_name = spotifyObject.current_user()['display_name'].split()[0]

    if playlist_name is None:
        playlist_name = first_name + '\'s Party'
        playlist_desc = ""

    party_playlist = spotifyObject.user_playlist_create(
        user_id, playlist_name, description=playlist_desc)

    return [first_name, user_id, party_playlist['id']]

def generate(host_token, guest_tokens, playlist_id):
    spotifyObject = spotipy.Spotify(auth=host_token)
    host_id = str(spotifyObject.current_user()['id'])

    # Collect collective top tracks and artists

    top_artists = {}
    top_tracks = {}

    for guest_token in guest_tokens:
        print(guest_token)
        guest_object = spotipy.Spotify(auth=guest_token)
        
        # Guest follows the playlist
        guest_object.user_playlist_follow_playlist(host_id, playlist_id)

        ranges = {'short_term': 8, 'medium_term': 9, 'long_term': 10}


        for range in ranges.keys():   

            guest_top_tracks = guest_object.current_user_top_tracks(limit=50, time_range=range)['items']

            for track in guest_top_tracks:
                if (track['name'], track['id']) in top_tracks:
                    top_tracks[(track['name'], track['id'])] += ranges[range]
                else:
                    top_tracks[(track['name'], track['id'])] = ranges[range]

            guest_top_artists = guest_object.current_user_top_artists(limit=50, time_range=range)['items']

            for artist in guest_top_artists:
                if (artist['name'], artist['id']) in top_artists:
                    top_artists[(artist['name'], artist['id'])] += ranges[range]
                else:
                    top_artists[(artist['name'], artist['id'])] = ranges[range]
                

    sorted_artists = {k: v for k, v in sorted(top_artists.items(), key=lambda item: item[1], reverse=True)}
    sorted_tracks = {k: v for k, v in sorted(top_tracks.items(), key=lambda item: item[1], reverse=True)}

    top_5_artists = {k: sorted_artists[k] for k in list(sorted_artists)[-5:]}

    # TO DO: given playlist length, determine number of top tracks to choose for playlist
    n = (len(guest_tokens) / 2) * 20
    print(n)

    most_common_tracks = []
    most_common_artists = []

    for track in sorted_tracks:
        print(track, sorted_tracks[track])
        if sorted_tracks[track] < n:
            break
        else:
            most_common_tracks.append(track[1])

    for artist in sorted_artists:
        print(artist, sorted_artists[artist])
        if sorted_artists[artist] < n:
            break
        else:
            most_common_artists.append(artist[1])


    most_common_tracks = most_common_tracks[:20]

    recommended_tracks = spotifyObject.recommendations(
        seed_artists=most_common_artists[:5], limit=15)
    track_ids = []
    for track in recommended_tracks['tracks']:
        track_ids.append(track['id'])

    recommended_tracks = spotifyObject.recommendations(
        seed_artists=most_common_artists[5:10], limit=15)
    for track in recommended_tracks['tracks']:
        track_ids.append(track['id'])

    track_ids.extend(most_common_tracks)

    print(track_ids)

    import random
    random.shuffle(track_ids)


    spotifyObject.user_playlist_add_tracks(
        host_id, playlist_id, track_ids)


def get_user(token):
    spotifyObject = spotipy.Spotify(auth=token)

    user = spotifyObject.me()
    profile_image = "https://lh3.googleusercontent.com/eN0IexSzxpUDMfFtm-OyM-nNs44Y74Q3k51bxAMhTvrTnuA4OGnTi_fodN4cl-XxDQc"
    if user['images']:
        profile_image = user['images'][0]
    return [user['display_name'].split()[0], user['id'], profile_image]