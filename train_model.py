"""
Model Training Module
Trains XGBoost classifier for fertilizer recommendation
"""
import logging
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from typing import Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from xgboost import XGBClassifier
from data_loader import FertilizerDataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FertilizerModelTrainer:
    """Train and evaluate XGBoost model for fertilizer prediction"""
    
    def __init__(self, data_dir: str = "backend/data", model_dir: str = "backend/models"):
        self.data_loader = FertilizerDataLoader(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.feature_importances = {}
        
    def train(self, filename: str = "train.csv", test_size: float = 0.2, random_state: int = 42):
        """
        Train XGBoost model
        
        Args:
            filename: CSV filename to load
            test_size: Proportion of data for testing
            random_state: Random seed
        """
        try:
            # Load and preprocess data
            logger.info("Loading dataset...")
            df = self.data_loader.load_dataset(filename)
            
            logger.info("Preprocessing data...")
            X, y = self.data_loader.preprocess_data(df)
            
            # Split data
            logger.info(f"Splitting data (test_size={test_size})...")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            logger.info(f"Training set: {X_train.shape[0]} samples")
            logger.info(f"Test set: {X_test.shape[0]} samples")
            
            # Initialize XGBoost model with optimized hyperparameters for high accuracy
            logger.info("Initializing XGBoost model with optimized parameters...")
            self.model = XGBClassifier(
                n_estimators=1000,
                learning_rate=0.03,
                max_depth=10,
                min_child_weight=2,
                subsample=0.85,
                colsample_bytree=0.85,
                gamma=0.05,
                reg_alpha=0.05,
                reg_lambda=0.5,
                random_state=random_state,
                objective='multi:softprob',
                eval_metric='mlogloss',
                n_jobs=-1,
                early_stopping_rounds=100,
                tree_method='hist'
            )
            
            # Train model
            logger.info("Training model...")
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Evaluate model
            logger.info("Evaluating model...")
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Model Accuracy: {accuracy:.4f}")
            
            # Classification report
            report = classification_report(y_test, y_pred, output_dict=True)
            logger.info(f"Classification Report:\n{classification_report(y_test, y_pred)}")
            
            # Extract feature importances (convert numpy types to Python types for JSON)
            feature_names = self.data_loader.get_feature_names()
            self.feature_importances = {
                name: float(importance) 
                for name, importance in zip(feature_names, self.model.feature_importances_)
            }
            
            # Save model and feature importances
            self.save_model()
            self.save_feature_importances()
            
            return {
                'accuracy': float(accuracy),
                'feature_importances': self.feature_importances,
                'classification_report': report
            }
        
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def save_model(self, filename: str = "fertilizer_model.pkl"):
        """Save trained model to disk"""
        try:
            model_path = self.model_dir / filename
            joblib.dump(self.model, model_path)
            logger.info(f"Model saved to: {model_path}")
            
            # Also save label encoders
            encoders_path = self.model_dir / "label_encoders.pkl"
            joblib.dump(self.data_loader.label_encoders, encoders_path)
            logger.info(f"Label encoders saved to: {encoders_path}")
            
            # Save target encoder
            target_encoder_path = self.model_dir / "target_encoder.pkl"
            joblib.dump(self.data_loader.target_encoder, target_encoder_path)
            logger.info(f"Target encoder saved to: {target_encoder_path}")
            
            # Save scaler
            scaler_path = self.model_dir / "scaler.pkl"
            joblib.dump(self.data_loader.scaler, scaler_path)
            logger.info(f"StandardScaler saved to: {scaler_path}")
            
            # Save feature columns
            feature_cols_path = self.model_dir / "feature_columns.pkl"
            joblib.dump(self.data_loader.get_feature_names(), feature_cols_path)
            logger.info(f"Feature columns saved to: {feature_cols_path}")
        
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def save_feature_importances(self, filename: str = "feature_importance.json"):
        """Save feature importances to JSON"""
        try:
            importance_path = self.model_dir / filename
            with open(importance_path, 'w') as f:
                json.dump(self.feature_importances, f, indent=2)
            logger.info(f"Feature importances saved to: {importance_path}")
        
        except Exception as e:
            logger.error(f"Error saving feature importances: {e}")
            raise
    
    def load_model(self, filename: str = "fertilizer_model.pkl"):
        """Load trained model from disk"""
        try:
            model_path = self.model_dir / filename
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            self.model = joblib.load(model_path)
            logger.info(f"Model loaded from: {model_path}")
            
            # Load label encoders
            encoders_path = self.model_dir / "label_encoders.pkl"
            if encoders_path.exists():
                self.data_loader.label_encoders = joblib.load(encoders_path)
                logger.info(f"Label encoders loaded from: {encoders_path}")
            
            # Load target encoder
            target_encoder_path = self.model_dir / "target_encoder.pkl"
            if target_encoder_path.exists():
                self.data_loader.target_encoder = joblib.load(target_encoder_path)
                self.data_loader.class_names = self.data_loader.target_encoder.classes_
                logger.info(f"Target encoder loaded from: {target_encoder_path}")
                logger.info(f"Fertilizer classes: {self.data_loader.class_names}")
            
            # Load feature columns
            feature_cols_path = self.model_dir / "feature_columns.pkl"
            if feature_cols_path.exists():
                feature_names = joblib.load(feature_cols_path)
                self.data_loader.feature_columns = feature_names
                logger.info(f"Feature columns loaded: {feature_names}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

def main():
    """Main function to train model"""
    trainer = FertilizerModelTrainer()
    
    # Try high-quality sample dataset first, fallback to train.csv
    try:
        results = trainer.train(filename="train_high_quality.csv")
    except FileNotFoundError:
        logger.info("High-quality dataset not found, using train.csv")
        results = trainer.train(filename="train.csv")
    
    print(f"\nTraining completed!")
    print(f"Accuracy: {results['accuracy']:.4f}")
    print(f"\nTop 5 Feature Importances:")
    sorted_features = sorted(results['feature_importances'].items(), key=lambda x: x[1], reverse=True)
    for feature, importance in sorted_features[:5]:
        print(f"  {feature}: {importance:.4f}")

if __name__ == "__main__":
    main()

