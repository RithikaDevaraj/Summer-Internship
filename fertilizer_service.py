"""
Fertilizer Service Module
Main service for ML-based fertilizer recommendations and comparisons
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
import joblib
from data_loader import FertilizerDataLoader
from kg_integration import FertilizerKGIntegration
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FertilizerService:
    """Service for ML-based fertilizer recommendations"""
    
    def __init__(self, model_dir: str = "backend/models", data_dir: str = "backend/data"):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.model = None
        self.data_loader = FertilizerDataLoader(data_dir)
        self.kg_integration = FertilizerKGIntegration()
        self.model_version = "1.0"
        self.model_loaded = False
        
        # Try to load model
        self.load_model()
    
    def load_model(self) -> bool:
        """Load trained XGBoost model"""
        try:
            model_path = self.model_dir / "fertilizer_model.pkl"
            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}. Run train_model.py first.")
                return False
            
            self.model = joblib.load(model_path)
            
            # Load label encoders
            encoders_path = self.model_dir / "label_encoders.pkl"
            if encoders_path.exists():
                self.data_loader.label_encoders = joblib.load(encoders_path)
                logger.info("Label encoders loaded")
            
            # Load target encoder
            target_encoder_path = self.model_dir / "target_encoder.pkl"
            if target_encoder_path.exists():
                self.data_loader.target_encoder = joblib.load(target_encoder_path)
                self.data_loader.class_names = self.data_loader.target_encoder.classes_
                logger.info(f"Target encoder loaded. Fertilizer classes: {self.data_loader.class_names}")
            else:
                logger.warning("Target encoder not found. Predictions may use numeric classes.")
            
            # Load scaler
            scaler_path = self.model_dir / "scaler.pkl"
            if scaler_path.exists():
                self.data_loader.scaler = joblib.load(scaler_path)
                logger.info("StandardScaler loaded")
            
            # Load feature columns
            feature_cols_path = self.model_dir / "feature_columns.pkl"
            if feature_cols_path.exists():
                self.data_loader.feature_columns = joblib.load(feature_cols_path)
                logger.info(f"Feature columns loaded: {self.data_loader.feature_columns}")
            
            self.model_loaded = True
            logger.info("Fertilizer ML model loaded successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_loaded = False
            return False
    
    def recommend_fertilizer(
        self,
        crop_name: str,
        soil_type: str,
        n: float,
        p: float,
        k: float,
        moisture: float,
        temperature: float,
        rainfall: Optional[float] = None,
        humidity: Optional[float] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Predict top K fertilizers for given crop conditions
        
        Args:
            crop_name: Name of crop
            soil_type: Type of soil (e.g., "Sandy", "Clayey")
            n: Nitrogen level
            p: Phosphorus level
            k: Potassium level
            moisture: Soil moisture
            temperature: Temperature
            rainfall: Rainfall (optional, can be derived from other features)
            humidity: Humidity (optional, can be derived from other features)
            top_k: Number of top recommendations to return
            
        Returns:
            List of dictionaries with 'name' and 'score' keys
        """
        try:
            if not self.model_loaded or not self.model:
                logger.warning("Model not loaded. Cannot make predictions.")
                return []
            
            # Encode categorical variables
            encoded = self.data_loader.encode_categorical_input(soil_type, crop_name)
            
            # Prepare base feature dictionary
            humidity_val = humidity if humidity is not None else 65.0
            feature_dict = {
                'Temperature': temperature,
                'Humidity': humidity_val,
                'Moisture': moisture,
                'Soil_Type': encoded.get('Soil_Type', 0),
                'Crop_Type': encoded.get('Crop_Type', 0),
                'Nitrogen': n,
                'Potassium': k,
                'Phosphorus': p
            }
            
            # Apply feature engineering (same as in preprocessing)
            # Add NPK interactions
            feature_dict['NPK_Total'] = n + p + k
            feature_dict['N_P_Ratio'] = n / (p + 1e-6)
            feature_dict['N_K_Ratio'] = n / (k + 1e-6)
            feature_dict['P_K_Ratio'] = p / (k + 1e-6)
            
            # Add climate interactions
            feature_dict['Temp_Humidity'] = temperature * humidity_val / 100
            feature_dict['Moisture_Humidity'] = moisture * humidity_val / 100
            
            # Prepare feature vector (get expected feature order)
            features = self.data_loader.get_feature_names()
            
            # Create base feature array (before scaling)
            base_feature_array = np.array([[feature_dict.get(col, 0.0) for col in features]])
            
            # Scale numeric features (same as training)
            if self.data_loader.scaler:
                numeric_cols = [col for col in features if col not in ['Soil_Type', 'Crop_Type']]
                numeric_indices = [i for i, col in enumerate(features) if col in numeric_cols]
                
                # Extract numeric values, scale, then put back
                feature_array = base_feature_array.copy()
                if numeric_indices:
                    numeric_values = base_feature_array[:, numeric_indices]
                    scaled_numeric = self.data_loader.scaler.transform(numeric_values)
                    feature_array[:, numeric_indices] = scaled_numeric
            else:
                feature_array = base_feature_array
            
            # Get predictions with probabilities
            probabilities = self.model.predict_proba(feature_array)[0]
            class_indices = np.argsort(probabilities)[::-1][:top_k]
            
            # Decode fertilizer names from encoded classes
            recommendations = []
            for idx in class_indices:
                # Decode using target encoder
                fertilizer_name = self.data_loader.decode_fertilizer_name(int(idx))
                score = float(probabilities[idx])
                
                recommendations.append({
                    'name': str(fertilizer_name),
                    'score': round(score, 4)
                })
                
                # Update KG with recommendation
                self.kg_integration.create_suitable_for_relationship(
                    crop_name=crop_name,
                    fertilizer_name=str(fertilizer_name),
                    score=score,
                    model_version=self.model_version
                )
            
            logger.info(f"Generated {len(recommendations)} recommendations for {crop_name}")
            return recommendations
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def compare_fertilizers(self, fertilizer_names: List[str]) -> Dict[str, Any]:
        """
        Compare fertilizers by retrieving info from KG
        
        Args:
            fertilizer_names: List of fertilizer names to compare
            
        Returns:
            Structured comparison dictionary
        """
        try:
            # Get fertilizer info from KG
            fertilizers = self.kg_integration.get_fertilizer_info(fertilizer_names)
            
            if not fertilizers:
                logger.warning(f"No fertilizer info found in KG for: {fertilizer_names}")
                return {
                    "fertilizers": [],
                    "count": 0,
                    "error": "Fertilizers not found in knowledge graph"
                }
            
            # Build comparison report
            comparison = {
                "fertilizers": fertilizers,
                "count": len(fertilizers),
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            return comparison
        
        except Exception as e:
            logger.error(f"Error comparing fertilizers: {e}")
            return {
                "fertilizers": [],
                "count": 0,
                "error": str(e)
            }
    
    def generate_recommendation_report(
        self,
        crop_name: str,
        soil_type: str,
        n: float,
        p: float,
        k: float,
        moisture: float,
        temperature: float,
        humidity: Optional[float] = None
    ) -> str:
        """
        Generate a text-based recommendation report
        
        Args:
            crop_name: Name of crop
            soil_type: Type of soil
            n, p, k: NPK values
            moisture: Soil moisture
            temperature: Temperature
            humidity: Humidity (optional)
            
        Returns:
            Text report string
        """
        try:
            recommendations = self.recommend_fertilizer(
                crop_name=crop_name,
                soil_type=soil_type,
                n=n,
                p=p,
                k=k,
                moisture=moisture,
                temperature=temperature,
                humidity=humidity,
                top_k=3
            )
            
            if not recommendations:
                return f"Unable to generate recommendations for {crop_name}. Model may not be trained or loaded."
            
            report_parts = [
                f"**Fertilizer Recommendations for {crop_name}**\n",
                f"Crop: {crop_name}",
                f"Soil Type: {soil_type}",
                f"NPK Levels - Nitrogen: {n}, Phosphorus: {p}, Potassium: {k}",
                f"Temperature: {temperature}°C",
                f"Moisture: {moisture}%\n",
                "**Top Recommendations:**\n"
            ]
            
            for idx, rec in enumerate(recommendations, 1):
                fertilizer_name = rec['name']
                score = rec['score']
                
                # Get fertilizer info from KG
                fertilizer_info = self.kg_integration.get_fertilizer_info([fertilizer_name])
                
                report_parts.append(f"\n**{idx}. {fertilizer_name}**")
                report_parts.append(f"   - Suitability Score: {score:.2%}")
                
                if fertilizer_info:
                    info = fertilizer_info[0]
                    if info.get('npk_ratio'):
                        report_parts.append(f"   - NPK Ratio: {info['npk_ratio']}")
                    if info.get('composition'):
                        report_parts.append(f"   - Composition: {info['composition']}")
                    if info.get('usage'):
                        report_parts.append(f"   - Usage: {info['usage']}")
                    if info.get('safety'):
                        report_parts.append(f"   - Safety: {info['safety']}")
                    if info.get('cost'):
                        report_parts.append(f"   - Cost: {info['cost']}")
            
            report_parts.append("\n*Recommendations generated using XGBoost ML model trained on Kaggle Optimal Fertilizers dataset*")
            
            return "\n".join(report_parts)
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating recommendation report: {str(e)}"
    
    def generate_comparison_report(self, fertilizer_names: List[str]) -> str:
        """
        Generate a text-based comparison report
        
        Args:
            fertilizer_names: List of fertilizer names to compare
            
        Returns:
            Text comparison report string
        """
        try:
            comparison = self.compare_fertilizers(fertilizer_names)
            
            if not comparison.get('fertilizers'):
                return f"No comparison data found for: {', '.join(fertilizer_names)}"
            
            fertilizers = comparison['fertilizers']
            
            report_parts = [
                "**Fertilizer Comparison Report**\n",
                f"Comparing {len(fertilizers)} fertilizers: {', '.join(fertilizer_names)}\n",
                "---\n"
            ]
            
            for fert in fertilizers:
                report_parts.append(f"\n**{fert['name']}**")
                report_parts.append(f"- Type: {fert.get('type', 'NPK-based')}")
                
                if fert.get('npk_ratio'):
                    report_parts.append(f"- NPK Ratio: {fert['npk_ratio']}")
                
                if fert.get('composition'):
                    report_parts.append(f"- Composition: {fert['composition']}")
                
                if fert.get('usage'):
                    report_parts.append(f"- Usage: {fert['usage']}")
                
                report_parts.append(f"- Safety: {fert.get('safety', 'Moderate')}")
                report_parts.append(f"- Cost: {fert.get('cost', 'Variable')}")
                
                if fert.get('suitable_crops'):
                    report_parts.append(f"- Suitable for: {', '.join(fert['suitable_crops'][:5])}")
                
                report_parts.append("")
            
            report_parts.append("*Data retrieved from Knowledge Graph*")
            
            return "\n".join(report_parts)
        
        except Exception as e:
            logger.error(f"Error generating comparison report: {e}")
            return f"Error generating comparison report: {str(e)}"

# Global service instance
fertilizer_service = FertilizerService()
