# Publishing on Kaggle

1. Edit `dataset-metadata.json`: replace `KAGGLE_USERNAME`.
2. Copy it next to the CSV files: `cp kaggle/dataset-metadata.json data/`
3. First release: `kaggle datasets create -p data`
4. Later releases: `kaggle datasets version -p data -m "TokWatt vX.Y.Z"`

Add the README, DATA_DICTIONARY and DATASHEET text to the Kaggle description, and link the GitHub repository.
