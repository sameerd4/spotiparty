import base64
import datetime
import json
import os
import random
import string
import sys
from collections import Counter
from urllib.parse import quote

import requests
import spotipy
import spotipy.util as util

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

#    library_list = []
    top_artists_list = []
    top_tracks_list = []

    for guest_token in guest_tokens:
        print(guest_token)
        guest_object = spotipy.Spotify(auth=guest_token)

        # Guest follows the playlist
        guest_object.user_playlist_follow_playlist(host_id, playlist_id)
        
        '''
        # Collect guest library
        guest_saved_tracks_ids = set()
        offset = 0
        guest_saved_tracks = guest_object.current_user_saved_tracks(limit=50, offset=offset)['items']

        while len(guest_saved_tracks) > 0:
            for track in guest_saved_tracks:
                guest_saved_tracks_ids.add(track['track']['id'])
            
            offset += 50
            guest_saved_tracks = guest_object.current_user_saved_tracks(limit=50, offset=offset)['items']

        library_list.append(guest_saved_tracks_ids)
        '''

        ranges = {'short_term': 8, 'medium_term': 9, 'long_term': 10}

        guest_top_tracks = {}
        guest_top_artists = {}

        for range in ranges.keys():   

            guest_top_tracks_range = guest_object.current_user_top_tracks(limit=50, time_range=range)['items']
            
            for track in guest_top_tracks_range:
                if (track['name'], track['id']) in guest_top_tracks:
                    guest_top_tracks[(track['name'], track['id'])] += ranges[range]
                else:
                    guest_top_tracks[(track['name'], track['id'])] = ranges[range]
            '''
            for track in guest_top_tracks_range:
                if track['name'] in guest_top_tracks:
                    guest_top_tracks[track['name']] += ranges[range]
                else:
                    guest_top_tracks[track['name']] = ranges[range]
            '''
            
            guest_top_artists_range = guest_object.current_user_top_artists(limit=50, time_range=range)['items']
            
            for artist in guest_top_artists_range:
                if (artist['name'], artist['id']) in guest_top_artists:
                    guest_top_artists[(artist['name'], artist['id'])] += ranges[range]
                else:
                    guest_top_artists[(artist['name'], artist['id'])] = ranges[range]
            '''
            for artist in guest_top_artists_range:
                if artist['name'] in guest_top_artists:
                    guest_top_artists[artist['name']] += ranges[range]
                else:
                    guest_top_artists[artist['name']] = ranges[range]
            '''

        top_tracks_list.append(guest_top_tracks)
        top_artists_list.append(guest_top_artists)

    group_favorite_tracks = [list(ttdict.keys()) for ttdict in top_tracks_list]
    group_favorite_artists = [list(tadict.keys()) for tadict in top_artists_list]

    from itertools import chain
    group_favorite_tracks_counter = Counter(chain(*group_favorite_tracks))
    group_favorite_artists_counter = Counter(chain(*group_favorite_artists)) 

    print(group_favorite_tracks_counter)
    print(group_favorite_artists_counter)

    favorite_track_candidates = set()

    for track in group_favorite_tracks_counter:
        if group_favorite_tracks_counter[track] >= 2 and len(guest_tokens) in [2,3]:
            favorite_track_candidates.add(track)
        else:
            if group_favorite_tracks_counter[track] >= (len(guest_tokens) // 2):
                favorite_track_candidates.add(track)

    print(len(favorite_track_candidates))
    if len(favorite_track_candidates) < 20:
        diff = 20 - len(favorite_track_candidates)
        num_tracks_to_get_from_guest = diff // len(guest_tokens)

        for guest_tracks_dict in top_tracks_list:
            favorite_track_candidates.update(random.sample(list(guest_tracks_dict.keys()), num_tracks_to_get_from_guest))
    else:
        favorite_track_candidates = set(random.sample(favorite_track_candidates, 20))

    print(favorite_track_candidates)
    track_ids = []
    favorite_artist_candidates = set()

    for artist in group_favorite_artists_counter:
        if group_favorite_artists_counter[artist] >= 2 and len(guest_tokens) in [2,3]:
            favorite_artist_candidates.add(artist)
        else:
            if group_favorite_artists_counter[artist] >= (len(guest_tokens) // 2):
                favorite_artist_candidates.add(artist)

    print(len(favorite_artist_candidates))
    if len(favorite_artist_candidates) < 20:
        diff = 20 - len(favorite_artist_candidates)
        num_artists_to_get_from_guest = diff // len(guest_tokens)

        for guest_artists_dict in top_artists_list:
            favorite_artist_candidates.update(random.sample(list(guest_artists_dict.keys()), num_artists_to_get_from_guest))

    seed_artists_ids = [i[1] for i in favorite_artist_candidates]
    seed_artists_ids = random.sample(seed_artists_ids, 10)

    if len(guest_tokens) > 1:
        recommended_tracks = spotifyObject.recommendations(seed_artists=seed_artists_ids[:5], limit=15)
        for track in recommended_tracks['tracks']:
            track_ids.append(track['id'])
        
        recommended_tracks = spotifyObject.recommendations(seed_artists=seed_artists_ids[5:10], limit=15)
        for track in recommended_tracks['tracks']:
            track_ids.append(track['id'])

    else:
        top_artists_ids = [i[1] for i in favorite_artist_candidates]
        recommended_tracks = spotifyObject.recommendations(seed_artists=seed_artists_ids[:5], limit=15)
        for track in recommended_tracks['tracks']:
            track_ids.append(track['id'])
        
        recommended_tracks = spotifyObject.recommendations(seed_artists=seed_artists_ids[5:10], limit=15)
        for track in recommended_tracks['tracks']:
            track_ids.append(track['id'])

    track_ids.extend([i[1] for i in favorite_track_candidates])

    print(track_ids)

    
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

token1 = 'BQB8ApPzlQNocs5vyzWsxAIZjgVQrY54GVRLZWKQOo2Klm8Tr0JmURaDCAXnF43am-6ReExWhJlMg_uYoctvRs8F-70LM3pAfFjNl7xb-kXvl5sreD5YHH8pV6J1xiVdfG1K4-Biv9UXNzOVSBchv77bB9lzstyUikAsGREvkdcEYiqvulTuNJW51yg'
token2 = 'BQCqKuKcsQqrasJqDywTcSoYLRykgXSxz3P60LRiqZtYc6d_oPd8FM4OLRUBNIYVsloZOuxszJhSIf7zGNMlupZamcx2jubOlpG1jOkmCk90uauVJ0Jc-jZl8V0vxJY2I5cqhPrHtR5Hq9RXcjnrsOISodGXq1A3vLV9DoeEFTYrgHb1jg2Oic1Juo8R'

generate(token1, [token1, token2], '4UBqwKjN1qucuNyrhLEoiA')