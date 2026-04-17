import streamlit as st
import pandas as pd
import requests
import random

# 1. API & Data Setup
TMDB_KEY = st.secrets["TMDB_API_KEY"]
CSV_FILE = "watch_data.csv"

st.set_page_config(page_title="Lunara Film | Bespoke Engine", page_icon="🎬", layout="wide")

@st.cache_data
def load_data_nuclear():
    try:
        # Step 1: Raw Scan to find the Header Row
        # This prevents the 'Expected 3 fields, saw 4' error by finding the real start
        skip_rows = 0
        with open(CSV_FILE, 'r', encoding='latin1') as f:
            for i, line in enumerate(f):
                if 'tmdb' in line.lower() and 'title' in line.lower():
                    skip_rows = i
                    break
        
        # Step 2: High-Precision Load
        df = pd.read_csv(
            CSV_FILE, 
            encoding='latin1', 
            skiprows=skip_rows,
            on_bad_lines='skip', 
            engine='python'
        )
        
        # Step 3: Absolute Column Normalization
        # We strip quotes, spaces, and force EVERYTHING to lowercase for zero-error matching
        df.columns = [str(c).strip().replace('"', '').replace("'", "").lower() for c in df.columns]
        
        # Standardize dates
        if 'watchedat' in df.columns:
            df['watchedat'] = pd.to_datetime(df['watchedat'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Nuclear Load Failed: {e}")
        return pd.DataFrame()

# Boot the Data
df = load_data_nuclear()

# Safety Check: If data failed to load, stop and warn Dalton
if df.empty:
    st.error("Critical Failure: No movie data could be parsed. Check your 'watch_data.csv' file on GitHub.")
    st.stop()

# 2. Bespoke Mapping (Now using absolute lowercase names)
# We use .get() to prevent KeyErrors forever
watched_ids = set(pd.to_numeric(df['tmdb'], errors='coerce').dropna().astype(int).tolist()) if 'tmdb' in df.columns else set()
ratings_available = 'rating' in df.columns

# UI Elements
st.sidebar.title("Lunara Film Engine")
st.sidebar.write(f"✅ Loaded {len(df)} films.")
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
        # Use movies rated 9 or 10 as seeds
        seed_pool = df[df['rating'] >= 9] if ratings_available else df
        if not seed_pool.empty:
            seeds = seed_pool.sample(min(3, len(seed_pool)))['tmdb'].tolist()
            pool = []
            for sid in seeds:
                try:
                    res = requests.get(f"https://api.themoviedb.org/3/movie/{int(sid)}/recommendations?api_key={TMDB_KEY}").json()
                    for r in res.get('results', []):
                        if r['id'] not in watched_ids: pool.append(r)
                except: continue
            
            if pool:
                picks = random.sample(pool, min(5, len(pool)))
                for m in picks: show_movie(m, "Based on your high-rated history.")
            else: st.write("Try again for more results.")

else:
    st.header("The Curator's Comfort")
    if st.button("Get Rewatch Targets"):
        favorites = df[df['rating'] >= 9] if ratings_available else df
        if not favorites.empty:
            picks = favorites.sample(min(5, len(favorites)))
            for _, row in picks.iterrows():
                try:
                    details = requests.get(f"https://api.themoviedb.org/3/movie/{int(row['tmdb'])}?api_key={TMDB_KEY}").json()
                    show_movie(details, f"Rewatch Target: Last rated {row.get('rating', 'N/A')}/10.")
                except: continue
