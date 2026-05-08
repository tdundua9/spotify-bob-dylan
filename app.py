"""Streamlit app for the Spotify + lyrics.ovh analysis."""
from __future__ import annotations

import ast, json, re, time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import streamlit as st
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import STOPWORDS, WordCloud

st.set_page_config(page_title="Spotify + Lyrics Explorer", page_icon="🎵", layout="wide")

DATA_FILE = Path("tracks_features.csv")
CACHE_PATH = Path("lyrics_cache.json")

ARTIST_PRESETS = {
    "Bob Dylan": {
        "artist_id": "74ASZWbe4lXaubB36ztrGX",
        "studio_albums": [
            ("Bob Dylan", 1962), ("The Freewheelin' Bob Dylan", 1963),
            ("The Times They Are a-Changin", 1964), ("Another Side of Bob Dylan", 1964),
            ("Bringing It All Back Home", 1965), ("Highway 61 Revisited", 1965),
            ("Blonde on Blonde", 1966), ("John Wesley Harding", 1967),
            ("Nashville Skyline", 1969), ("Self Portrait", 1970),
            ("New Morning", 1970), ("Dylan", 1973), ("Planet Waves", 1974),
            ("Blood on the Tracks", 1975), ("The Basement Tapes", 1975),
            ("Desire", 1976), ("Street-Legal", 1978),
            ("Slow Train Coming", 1979), ("Saved", 1980), ("Shot of Love", 1981),
            ("Infidels", 1983), ("Empire Burlesque", 1985),
            ("Knocked Out Loaded", 1986), ("Down in the Groove", 1988),
            ("Oh Mercy", 1989), ("Under the Red Sky", 1990),
            ("Good as I Been to You", 1992), ("World Gone Wrong", 1993),
            ("Time Out of Mind", 1997), ("Love and Theft", 2001),
            ("Modern Times", 2006), ("Together Through Life", 2009),
            ("Christmas in the Heart", 2009), ("Tempest", 2012),
            ("Shadows in the Night", 2015), ("Fallen Angels", 2016),
            ("Triplicate", 2017), ("Rough and Rowdy Ways", 2020),
        ],
    },
    "Radiohead": {
        "artist_id": "4Z8W4fKeB5YxbusRsdQVPb",
        "studio_albums": [
            ("Pablo Honey", 1993), ("The Bends", 1995), ("OK Computer", 1997),
            ("Kid A", 2000), ("Amnesiac", 2001), ("Hail to the Thief", 2003),
            ("In Rainbows", 2007), ("The King of Limbs", 2011),
            ("A Moon Shaped Pool", 2016),
        ],
    },
}

EXTRA_STOPWORDS = {
    "yeah", "oh", "uh", "gonna", "wanna", "gotta", "tryna",
    "la", "na", "huh", "hey", "ho", "im", "youre", "theyre", "were",
    "cause", "cuz", "em", "know", "like", "just", "got", "get", "one",
    "verse", "chorus", "bridge", "outro", "intro", "ill", "youll",
    "dont", "doesnt", "didnt", "cant", "wont", "thats",
}

REISSUE_BLACKLIST = re.compile(
    r"\b(bootleg series|karaoke|tribute|workout|covers?|orchestrat|instrumental|"
    r"a cappella|acapella|live (at|in|from)|in concert|unplugged|"
    r"mixtape|sampler|playlist|compilation|greatest hits|anthology|"
    r"the very best|essentials|biograph|collection|hits|original mono|"
    r"mono recordings|witmark demos|complete album|\bdemos\b)\b",
    flags=re.I,
)


@st.cache_data(show_spinner="Loading dataset…")
def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        try:
            import gdown
        except ImportError:
            return pd.DataFrame()
        with st.spinner("Downloading dataset (~346 MB, one-time)…"):
            gdown.download(id="1jsXTNtGhOrsCApQctYx-hRxAQASAcPlI",
                           output=str(path), quiet=True)
        if not path.exists():
            return pd.DataFrame()
    return pd.read_csv(path)


def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s&]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def short_album_name(album: str) -> str:
    return re.split(r"[\(\[:]", str(album), maxsplit=1)[0].strip()


def match_studio_album(short_name, original_album, canon_set):
    if REISSUE_BLACKLIST.search(original_album):
        return None
    norm = normalize(short_name)
    if norm in canon_set:
        return canon_set[norm]
    for cn, c in canon_set.items():
        if (norm.startswith(cn) or cn.startswith(norm)) and len(cn) >= 4 and len(norm) >= 4:
            return c
    return None


@st.cache_data(show_spinner=False)
def filter_artist(df, artist_id, canonical):
    def in_list(s):
        try:
            return artist_id in ast.literal_eval(s)
        except (ValueError, SyntaxError):
            return False

    sub = df[df["artist_ids"].apply(lambda x: in_list(str(x)))].copy()
    if sub.empty:
        sub["canonical_album"] = pd.Series(dtype=object)
        return sub
    sub["short_album_name"] = sub["album"].apply(short_album_name)
    canon_set = {normalize(a): a for a, _ in canonical}
    sub["canonical_album"] = [
        match_studio_album(sn, al, canon_set)
        for sn, al in zip(sub["short_album_name"], sub["album"])
    ]
    sub = sub[sub["canonical_album"].notna()].copy()
    sub = (sub.sort_values("year")
           .drop_duplicates(subset=["canonical_album", "name"], keep="first")
           .reset_index(drop=True))
    return sub


def load_cache():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_title(title):
    t = title
    t = re.sub(r"\s*-\s*(Remaster|Remastered|Live|Edit|Mono|Stereo).*$", "", t, flags=re.I)
    t = re.sub(r"\s*\(feat\.[^)]*\)", "", t, flags=re.I)
    t = re.sub(r"\s*\[feat\.[^\]]*\]", "", t, flags=re.I)
    t = re.sub(r"\s*\(with[^)]*\)", "", t, flags=re.I)
    t = re.sub(r"\s*\(Bonus Track\)", "", t, flags=re.I)
    return t.strip()


def fetch_lyrics(artist, title, cache, sleep=0.4):
    key = f"{artist.lower()}::{title.lower()}"
    if key in cache:
        return cache[key]
    url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(clean_title(title))}"
    try:
        r = requests.get(url, timeout=10)
        lyrics = r.json().get("lyrics", "") if r.status_code == 200 else ""
    except Exception:
        lyrics = ""
    cache[key] = lyrics
    time.sleep(sleep)
    return lyrics


def fetch_all_lyrics(artist, songs, progress_cb=None):
    cache = load_cache()
    total = len(songs)
    found = 0
    for i, title in enumerate(songs, 1):
        text = fetch_lyrics(artist, title, cache)
        if text:
            found += 1
        if progress_cb:
            progress_cb(i, total, found)
        if i % 10 == 0:
            save_cache(cache)
    save_cache(cache)
    return cache


def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z\s']", " ", text)
    return [w for w in text.split()
            if len(w) > 2 and w not in STOPWORDS and w not in EXTRA_STOPWORDS]


st.title("🎵 Spotify + Lyrics Explorer")
st.caption("Studio-only discography from Wikipedia + lyrics from lyrics.ovh.")

with st.sidebar:
    st.header("Settings")
    artist_name = st.selectbox("Artist", list(ARTIST_PRESETS.keys()), index=0)
    cfg = ARTIST_PRESETS[artist_name]
    st.markdown(f"**Artist ID:** `{cfg['artist_id']}`")
    st.markdown(f"**Studio albums (Wikipedia):** {len(cfg['studio_albums'])}")


df = load_dataset(DATA_FILE)
if df.empty:
    st.stop()

studio_df = filter_artist(df, cfg["artist_id"], tuple(cfg["studio_albums"]))
album_order = [a for a, _ in cfg["studio_albums"] if a in set(studio_df["canonical_album"])]

if studio_df.empty:
    st.warning("No tracks found for this artist in the dataset.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tracks (studio)", len(studio_df))
c2.metric("Albums found", len(album_order))
c3.metric("Years", f"{studio_df['year'].min()}–{studio_df['year'].max()}")
c4.metric("Mean duration (min)", f"{studio_df['duration_ms'].mean()/60000:.1f}")

tab_albums, tab_audio, tab_lyrics, tab_top = st.tabs(
    ["Albums", "Audio features", "Lyrics", "Top words"]
)

with tab_albums:
    st.subheader("Tracks per studio album")
    counts = studio_df.groupby("canonical_album")["name"].count().reindex(album_order)
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(album_order) + 1))
    ax.barh(counts.index, counts.values, color="steelblue")
    ax.invert_yaxis()
    ax.set_xlabel("Number of tracks")
    fig.tight_layout()
    st.pyplot(fig)

    st.subheader("Tracks")
    sel_album = st.selectbox("Album", album_order)
    rows = studio_df[studio_df["canonical_album"] == sel_album][
        ["name", "year", "duration_ms", "danceability", "energy", "valence"]
    ].copy()
    rows["duration"] = (rows["duration_ms"] / 1000).round().astype(int).astype(str) + " s"
    st.dataframe(
        rows[["name", "year", "duration", "danceability", "energy", "valence"]]
        .rename(columns={"name": "Song", "year": "Year"}),
        use_container_width=True, hide_index=True,
    )

with tab_audio:
    st.subheader("Valence vs Energy by album")
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.scatterplot(data=studio_df, x="valence", y="energy",
        hue="canonical_album", hue_order=album_order, palette="tab20",
        size="duration_ms", sizes=(40, 500), alpha=0.85, ax=ax)
    h, l = ax.get_legend_handles_labels()
    n = len(album_order)
    ax.legend(h[1:n+1], l[1:n+1], title="Album", fontsize=7,
              loc="center left", bbox_to_anchor=(1.02, 0.5))
    fig.tight_layout()
    st.pyplot(fig)

    st.subheader("Mean features per album (normalised)")
    radar_features = ["acousticness", "danceability", "energy",
                      "instrumentalness", "speechiness", "valence"]
    means = studio_df.groupby("canonical_album")[radar_features].mean().reindex(album_order)
    norm = (means - means.min()) / (means.max() - means.min() + 1e-9)
    fig, ax = plt.subplots(figsize=(9, max(5, 0.3 * len(album_order))))
    sns.heatmap(norm, cmap="RdYlBu_r", annot=False, ax=ax)
    fig.tight_layout()
    st.pyplot(fig)

with tab_lyrics:
    st.subheader("Lyrics download")
    st.caption("Cached in `lyrics_cache.json`.")

    if "lyrics_loaded_for" not in st.session_state:
        st.session_state.lyrics_loaded_for = None

    if st.button(f"Download lyrics for {artist_name}",
                 key="dl_lyrics",
                 disabled=st.session_state.lyrics_loaded_for == artist_name):
        progress = st.progress(0.0, text="Starting…")
        def cb(i, total, found):
            progress.progress(i / total, text=f"{i}/{total} - found: {found}")
        fetch_all_lyrics(artist_name, studio_df["name"].tolist(), progress_cb=cb)
        progress.empty()
        st.session_state.lyrics_loaded_for = artist_name
        st.success("Done.")

    cache = load_cache()
    def lookup(name):
        return cache.get(f"{artist_name.lower()}::{name.lower()}", "")

    studio_df["lyrics"] = studio_df["name"].apply(lookup)
    found = studio_df["lyrics"].str.len().gt(0).sum()
    st.info(f"Lyrics in cache: {found}/{len(studio_df)} ({found/len(studio_df):.0%})")

    if found == 0:
        st.warning("No lyrics yet. Click the button above.")
        st.stop()

    st.subheader("Word cloud")
    corpus = " ".join(studio_df["lyrics"].dropna().tolist())
    tokens = tokenize(corpus)
    if tokens:
        wc = WordCloud(width=1100, height=520, background_color="white",
                       colormap="viridis", max_words=200).generate(" ".join(tokens))
        fig, ax = plt.subplots(figsize=(13, 6))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

    st.subheader("Sentiment per album (VADER)")
    sia = SentimentIntensityAnalyzer()
    studio_df["sentiment"] = studio_df["lyrics"].apply(
        lambda t: sia.polarity_scores(t)["compound"] if t else np.nan
    )
    sent = (studio_df.dropna(subset=["sentiment"])
            .groupby("canonical_album")["sentiment"]
            .agg(["mean", "std", "count"])
            .reindex(album_order).dropna(subset=["mean"]))
    if not sent.empty:
        colors = ["#d62728" if v < 0 else "#2ca02c" for v in sent["mean"]]
        fig, ax = plt.subplots(figsize=(9, 0.5 * len(sent) + 1))
        ax.barh(sent.index, sent["mean"],
                xerr=sent["std"] / np.sqrt(sent["count"].clip(lower=1)),
                color=colors, alpha=0.85)
        ax.axvline(0, color="black", linewidth=0.7)
        ax.set_xlabel("Mean compound score")
        ax.invert_yaxis()
        fig.tight_layout()
        st.pyplot(fig)
        st.dataframe(sent.round(3), use_container_width=True)

    st.subheader("Lexical richness")
    def album_stats(group):
        text = " ".join(group["lyrics"].dropna())
        toks = tokenize(text)
        n_songs = group["lyrics"].str.len().gt(0).sum()
        return pd.Series({
            "Songs with lyrics": n_songs,
            "Total tokens": len(toks),
            "Unique vocab": len(set(toks)),
            "TTR": round(len(set(toks)) / len(toks), 3) if toks else np.nan,
            "Words / song": round(len(toks) / n_songs, 1) if n_songs else np.nan,
        })
    lex = studio_df.groupby("canonical_album").apply(album_stats).reindex(album_order)
    st.dataframe(lex, use_container_width=True)

    st.subheader("Read a song")
    songs = studio_df[studio_df["lyrics"].str.len().gt(0)]["name"].tolist()
    if songs:
        pick = st.selectbox("Song", songs, key="pick_song")
        st.text_area("Lyrics", lookup(pick), height=300)

with tab_top:
    st.subheader("Top words per album")
    cache = load_cache()
    def lookup(name):
        return cache.get(f"{artist_name.lower()}::{name.lower()}", "")
    studio_df["lyrics"] = studio_df["name"].apply(lookup)
    rows = []
    for album in album_order:
        text = " ".join(studio_df.loc[studio_df["canonical_album"] == album, "lyrics"].dropna())
        toks = tokenize(text)
        top = Counter(toks).most_common(15) if toks else []
        rows.append({"Album": album, "Top 15": ", ".join(w for w, _ in top) or "-"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
