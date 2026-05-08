# Spotify + Lyrics analysis: Bob Dylan

Files:

- `Spotify_Bob_Dylan.ipynb` - notebook (parts 1 and 2)
- `app.py` - Streamlit web app (part 3)
- `lyrics_ovh_extractor.py`, `enhanced_lyrics_retriever.py` - lyrics helpers from the dist.zip
- `requirements.txt` - dependencies
- `lyrics_cache.json` - lyrics cache (created on first run)
- `build_notebook.py` - script that produces the .ipynb

## Run

```bash
pip install -r requirements.txt
python build_notebook.py        # generates the .ipynb
streamlit run app.py            # web app
```

The notebook downloads `tracks_features.csv` (~346 MB) from Google Drive on first
run, or you can place it manually in this folder.

## Export

```bash
jupyter nbconvert --to html Spotify_Bob_Dylan.ipynb
```
