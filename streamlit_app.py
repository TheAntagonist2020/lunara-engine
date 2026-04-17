import streamlit as st
import pandas as pd
import requests
import random

# 1. API & Data Setup
TMDB_KEY = st.secrets["TMDB_API_KEY"]
CSV_FILE = "watch_data.csv" # Ensure your file on GitHub is named watch_data.csv

st.set_page_config(page_title="Lunara Film | Bespoke Engine", page_icon="🎬", layout="wide")

@st.cache_data
def load_data():
    try:
        # KERNEL-HARDENED PARSER: Forcing comma separation and skipping broken rows
        df = pd.read_csv(
            CSV_FILE, 
            encoding='latin1', 
            sep=',', 
            on_bad_lines='skip', 
            engine='python'
        )
        # COLUMN SCRUBBING: Removes hidden characters, spaces, or quotes from headers
        df.columns = [str(c).strip().replace('"', '').replace("'", "") for c in df.columns]
        
        if 'WatchedAt' in df.columns:
            df['WatchedAt'] = pd.to_datetime(df['WatchedAt'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Critical System Failure during data ingestion: {e}")
        return pd.DataFrame()

df = load_data()

# ROBUST COLUMN MAPPING: Prevents KeyError by searching for columns dynamically
tmdb_col = next((c for c in df.columns if 'tmdb' in c.lower()), None)
rating_col = next((c for c in df.columns if 'rating' in c.lower()), None)
title_col = next((c for c in df.columns if 'title' in c.lower()), 'Title')

if tmdb_col:
    # Create the exclusion list
    watched_ids = set(pd.to_numeric(df[tmdb_col], errors='coerce').dropna().astype(int).tolist())
else:
    st.warning("Data-Link Warning: 'TMDb' column not found. All results will be treated as 'New'.")
    watched_ids = set()

# 2. UI Elements
st.sidebar.title("Lunara Film Engine")
st.sidebar.write("Operator: Dalton")
st.sidebar.caption(f"Loaded {len(df)} films from history.")

mode = st.sidebar.radio("Select Workflow", ["Discovery (Evolution)", "Rewatch (Comfort)"])

st.title("🎬 Bespoke Recommendation Engine")

def show_movie(movie, reason=""):
    with st.container():
        col1, col2 = st.columns([1, 4])
        with col1:
            if movie.get('poster_path'):
                st.image(f"https://image.tmdb.org/t_p/w500{movie['poster_path']}")
        with col2:
            st.subheader(movie.get('title', 'Unknown Title'))
            st.caption(f"💡 {reason}")
            st.write(movie.get('overview', 'No summary available.'))
        st.divider()

# 3. Logic Execution
if mode == "Discovery (Evolution)":
    st.header("The Critic's Evolution")
    if st.button("Generate Discoveries"):
        # Identify your 10/10 seeds
        if rating_col and tmdb_col:
            top_rated = df[df[rating_col] >= 9].copy()
            if not top_rated.empty:
                seeds = top_rated.sample(min(3, len(top_rated)))[tmdb_col].tolist()
                pool = []
                for sid in seeds:
                    res = requests.get(f"https://api.themoviedb.org/3/movie/{int(sid)}/recommendations?api_key={TMDB_KEY}").json()
                    for r in res.get('results', []):
                        if r['id'] not in watched_ids:
                            pool.append(r)
                
                if pool:
                    picks = random.sample(pool, min(5, len(pool)))
                    for m in picks:
                        show_movie(m, "Based on your high-rated history.")
                else:
                    st.write("No new discoveries found for these seeds. Try again.")
            else:
                st.write("No films rated 9 or 10 found in your data.")
        else:
            st.write("TMDb or Rating data missing from file.")

else:
    st.header("The Curator's Comfort")
    if st.button("Get Rewatch Targets"):
        if rating_col and tmdb_col:
            favorites = df[df[rating_col] >= 9].copy()
            if not favorites.empty:
                picks = favorites.sample(min(5, len(favorites)))
                for _, row in picks.iterrows():
                    details = requests.get(f"https://api.themoviedb.org/3/movie/{int(row[tmdb_col])}?api_key={TMDB_KEY}").json()
                    show_movie(details, f"Rewatch Target: You rated this {row[rating_col]}/10.")
            else:
                st.write("No high-rated films found for rewatching.")
