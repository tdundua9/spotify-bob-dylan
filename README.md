# Spotify + Lyrics analysis: Bob Dylan

Files:

* `Spotify_Bob_Dylan.ipynb` - notebook for parts 1 and 2 of the assignment
* `Spotify_Bob_Dylan.html` - HTML export of the notebook
* `app.py` - Streamlit web app (part 3)
* `URL.txt` - public URL of the deployed web app
* `requirements.txt` - dependencies
* `README.md` - project description and instructions
* `tracks_small.csv` - filtered dataset for the deployed app

## Run

```bash
pip install -r requirements.txt
streamlit run app.py            # web app
jupyter notebook Spotify_Bob_Dylan.ipynb   # notebook
```

The notebook uses the original `tracks_features.csv` dataset. Because it is large (~346 MB), it is downloaded automatically when the notebook is run. The Streamlit app uses `tracks_small.csv`.

## Export to HTML

```bash
jupyter nbconvert --to html Spotify_Bob_Dylan.ipynb
```
