# Fertilizer ML Model Training Guide

## Overview
The fertilizer recommendation system uses an XGBoost classifier trained on the Kaggle "Optimal Fertilizers" dataset.

## Prerequisites
1. Ensure CSV files are in `backend/data/`:
   - `train.csv` (or `Fertilizer Prediction.csv`)
   - `test.csv` (optional)

2. Install required dependencies:
   ```bash
   pip install xgboost scikit-learn pandas joblib numpy
   ```

## Training the Model

### Step 1: Train the Model
Run the training script:
```bash
cd backend
python train_model.py
```

This will:
- Load and preprocess the dataset
- Split into train/test sets (80/20)
- Train XGBoost classifier
- Evaluate model performance
- Save model to `backend/models/fertilizer_model.pkl`
- Save label encoders to `backend/models/label_encoders.pkl`
- Save feature columns to `backend/models/feature_columns.pkl`
- Save feature importances to `backend/models/feature_importance.json`

### Step 2: Verify Model Files
After training, verify these files exist in `backend/models/`:
- `fertilizer_model.pkl` - Trained XGBoost model
- `label_encoders.pkl` - Label encoders for categorical variables
- `feature_columns.pkl` - Feature column names
- `feature_importance.json` - Feature importance scores

### Step 3: Start the Backend
The `fertilizer_service` will automatically load the model on startup:
```bash
python main.py
```

## Model Parameters
The XGBoost model uses these default parameters:
- `n_estimators`: 300
- `learning_rate`: 0.1
- `max_depth`: 6
- Early stopping after 20 rounds

## Dataset Format
Expected columns in CSV:
- `id` - Unique identifier (optional)
- `Temparature` (note: typo in original) - Temperature in Celsius
- `Humidity` - Humidity percentage
- `Moisture` - Soil moisture percentage
- `Soil Type` - Categorical (Sandy, Clayey, Loamy, Silty)
- `Crop Type` - Categorical (Rice, Wheat, Cotton, etc.)
- `Nitrogen` - Nitrogen level
- `Potassium` - Potassium level
- `Phosphorous` - Phosphorus level (note: spelling)
- `Fertilizer Name` - Target variable (NPK ratios like "28-28", "17-17-17")

## Troubleshooting

### Model Not Found Error
If you see "Model file not found", ensure you've trained the model first:
```bash
python train_model.py
```

### Feature Mismatch Error
If features don't match, retrain the model with the current dataset:
```bash
python train_model.py
```

### Poor Model Performance
- Check dataset quality and completeness
- Adjust XGBoost hyperparameters in `train_model.py`
- Ensure sufficient training samples

## Model Evaluation
After training, check:
1. Accuracy score (printed to console)
2. Classification report (printed to console)
3. Feature importances (saved to JSON)

