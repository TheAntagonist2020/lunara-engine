import streamlit as st
import pandas as pd
import requests
import random

# 1. API & Data Setup
TMDB_KEY = st.secrets["TMDB_API_KEY"]
CSV_FILE = "watch_data.csv"
st.set_page_config(page_title="Lunara Film | Bespoke Engine", layout="wide")

@st.cache_data
def load_data():
    # Structural Hardening: Use engine='python' to auto-detect separators 
    # and handle titles containing commas.
    try:
        df = pd.read_csv(
            CSV_FILE, 
            encoding='latin1', 
            sep=None,            # Auto-detect if it's comma, tab, or semicolon
            engine='python',      # More flexible than the standard C engine
            on_bad_lines='warn'   # Skip corrupt lines instead of crashing the app
        )
    except Exception as e:
        st.error(f"Critical Data Error: {e}")
        return pd.DataFrame() # Return empty to prevent session collapse

    # Ensure date columns are formatted for logic
    if 'WatchedAt' in df.columns:
        df['WatchedAt'] = pd.to_datetime(df['WatchedAt'], errors='coerce')
    
    return df

df = load_data()
watched_ids = set(df['TMDb'].tolist())

# 2. UI Elements
st.sidebar.title("Lunara Film Engine")
st.sidebar.write("Operator: Dalton")
mode = st.sidebar.radio("Select Workflow", ["Discovery (Evolution)", "Rewatch (Comfort)"])

st.title("🎬 Bespoke Recommendation Engine")

def show_movie(movie, reason=""):
    with st.container():
        col1, col2 = st.columns([1, 4])
        with col1:
            if movie.get('poster_path'):
                st.image(f"https://image.tmdb.org/t_p/w500{movie['poster_path']}")
        with col2:
            st.subheader(movie['title'])
            st.caption(f"💡 {reason}")
            st.write(movie.get('overview', 'No summary available.'))
        st.divider()

# 3. Logic Execution
if mode == "Discovery (Evolution)":
    st.header("The Critic's Evolution")
    if st.button("Generate Discoveries"):
        # Use 10-rated films as seeds
        seeds = df[df['Rating'] == 10].sample(3)['TMDb'].tolist()
        pool = []
        for sid in seeds:
            res = requests.get(f"https://api.themoviedb.org/3/movie/{sid}/recommendations?api_key={TMDB_KEY}").json()
            for r in res.get('results', []):
                if r['id'] not in watched_ids: pool.append(r)
        
        for m in random.sample(pool, 5):
            show_movie(m, "Based on your 10/10 ratings")

else:
    st.header("The Curator's Comfort")
    if st.button("Get Rewatch Targets"):
        favorites = df[df['Rating'] >= 9].copy()
        favorites['days_since'] = (pd.Timestamp.now(tz='UTC') - favorites['WatchedAt']).dt.days
        picks = favorites.sort_values(by='days_since', ascending=False).head(20).sample(5)
        for _, row in picks.iterrows():
            details = requests.get(f"https://api.themoviedb.org/3/movie/{row['TMDb']}?api_key={TMDB_KEY}").json()
            show_movie(details, f"Rated {row['Rating']}/10. Last seen {row['days_since']} days ago.")
