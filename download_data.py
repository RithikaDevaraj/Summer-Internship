import os
from kaggle.api.kaggle_api_extended import KaggleApi

def download_fertilizer_data():
    api = KaggleApi()
    api.authenticate()
    
    # Download competition data
    api.competition_download_file(
        'playground-series-s5e6',
        'train.csv',
        path='data'
    )
    api.competition_download_file(
        'playground-series-s5e6',
        'test.csv',
        path='data'
    )
    
    # Download original dataset
    api.dataset_download_file(
        'atharvaingle/fertilizer-prediction',
        'Fertilizer Prediction.csv',
        path='data'
    )

if __name__ == "__main__":
    download_fertilizer_data()