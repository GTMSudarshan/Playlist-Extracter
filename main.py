import csv
import os
import sys
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import spotipy
import time # For a small delay

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials from .env
# Ensure these environment variables are named SPOTIPY_... as per Spotipy's expectation
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI") # This should be your Codespace's public URL

# Check if credentials are loaded
if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    print("Error: Missing Spotify API credentials in .env file or incorrect variable names.")
    print("Please ensure SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI are set.")
    print("And that SPOTIPY_REDIRECT_URI matches the one registered in your Spotify Developer App.")
    sys.exit(1) # Exit if credentials are missing

# Define the scope of access needed
SCOPE = "playlist-read-private playlist-read-collaborative"

# --- SPOTIPY AUTHENTICATION FLOW (Codespaces Friendly) ---
# Spotipy will launch a local server and expect the redirect to hit it.
# Because Codespaces forwards the port, this should work.
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache", # Caches the token so you don't re-authorize every time
    show_dialog=True # Forces re-authorization prompt if needed, helpful for initial setup
))

print("\nAttempting Spotify authentication...")
print("If a browser window doesn't open automatically, look for a new tab/window request")
print("or navigate to the 'Ports' tab in your Codespace and click on the forwarded link for port 8888 (or whatever is configured).")
print("You might need to manually click 'Authorize' in your browser.")
print("Waiting for authentication to complete...")

# We don't need to manually capture the redirect URL here because
# spotipy's built-in server should capture it if the REDIRECT_URI is correctly set up for Codespaces.
# A small delay to allow the server to start and browser interaction to happen.
time.sleep(2) 

# Test authentication by fetching current user (requires user scope)
try:
    user_info = sp.current_user()
    print(f"\n✅ Spotify authentication successful! Logged in as: {user_info['display_name']}")
except spotipy.exceptions.SpotifyException as e:
    print(f"\nError during Spotify authentication: {e}")
    print("This usually means: ")
    print("1. The REDIRECT_URI in your .env doesn't exactly match the one in Spotify Developer App.")
    print("2. You didn't authorize the app in your browser after it opened.")
    print("3. There's an issue with your CLIENT_ID or CLIENT_SECRET.")
    sys.exit(1)


def extract_playlist_tracks(playlist_url):
    # Validate the URL before attempting to split
    if "open.spotify.com/playlist/" not in playlist_url:
        print("Error: Invalid Spotify playlist URL. Please provide a direct link to a playlist.")
        return

    # Extract playlist ID from URL
    try:
        playlist_id = playlist_url.split("playlist/")[1].split("?")[0]
    except IndexError:
        print("Error: Could not parse playlist ID from the URL. Please ensure it's a valid Spotify playlist URL.")
        return
    
    # Fetch playlist tracks
    try:
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']

        # Fetch all tracks if the playlist is long
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error fetching playlist tracks: {e}")
        print("Please check the playlist ID/URL or your Spotify API permissions for this playlist.")
        return

    track_data_raw = []
    for item in tracks:
        track = item['track']
        if track is None: # Sometimes a track might be None (e.g., if it was removed or is local file)
            continue
        name = track['name']
        # Join all artists if there are multiple
        artists = ', '.join([artist['name'] for artist in track['artists']])
        track_data_raw.append(f"{name} - {artists}")

    filename = "playlist_export.csv"
    existing_entries = set()
    
    # Check if the file exists and has content before attempting to read
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0

    # Read existing entries if file exists, to avoid adding duplicates
    if file_exists:
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None) # Skip header row if present
            for row in reader:
                if len(row) > 1: # Ensure row has at least two columns (Index, Track)
                    existing_entries.add(row[1]) # Add the track string to the set

    new_unique_tracks = []
    for entry in track_data_raw:
        if entry not in existing_entries:
            new_unique_tracks.append(entry)
            existing_entries.add(entry) # Add to set to prevent duplicates if processing same list multiple times

    # Append new unique tracks to the CSV
    # Using 'a' mode to append, 'w' mode would overwrite
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists: # Write header only if the file was just created
            writer.writerow(["Index", "Track"])
        
        # Determine starting index for new entries
        # If file existed and had data, index new items from there
        if file_exists:
             # Count existing unique tracks in the file (assuming no duplicates from previous runs)
            start_index = len(existing_entries) - len(new_unique_tracks) + 1 # Calculate based on final set size
        else:
            start_index = 1 # Start from 1 if it's a new file

        for idx, entry in enumerate(new_unique_tracks):
            writer.writerow([start_index + idx, entry])

    print(f"Exported {len(new_unique_tracks)} new unique tracks to {filename}.")
    print(f"Total unique tracks now in '{filename}': {len(existing_entries)}")


if __name__ == '__main__':
    url = input("Paste your Spotify playlist URL: ").strip() # .strip() to remove leading/trailing whitespace
    extract_playlist_tracks(url)