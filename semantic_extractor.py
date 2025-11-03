import logging
from typing import Dict, List, Any, Tuple, Optional
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sentence transformers, fallback to keyword-only if not available
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("sentence-transformers not installed, using keyword-only extraction")

class SemanticExtractor:
    """Hybrid entity/intent extractor using keywords + semantic embeddings"""
    
    def __init__(self):
        self.model = None
        if SEMANTIC_AVAILABLE:
            try:
                # Lightweight model for fast inference
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Semantic extractor initialized with all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}, falling back to keywords")
                self.model = None
        
        # Intent templates for semantic matching
        self.intent_templates = {
            "market_price": [
                "What is the price of {commodity}",
                "price of {commodity} in {location}",
                "market rate for {commodity}",
                "cost of {commodity}",
                "how much does {commodity} cost",
                "compare prices of {commodity} and {commodity2}",
                "price comparison between {commodity} and {commodity2}",
                "{commodity} rates in {location}",
                "mandi price for {commodity}",
            ],
            "weather": [
                "weather in {location}",
                "temperature in {location}",
                "rainfall forecast for {location}",
                "current weather {location}",
                "weather conditions in {location}",
            ],
            "advisory": [
                "how to control {pest} in {crop}",
                "treatment for {disease}",
                "management of {crop} pests",
                "best practices for {crop}",
                "advice on {crop} cultivation",
            ]
        }
        
        # Commodity entity templates (for validation)
        self.commodity_templates = [
            "onion", "tomato", "coconut", "rice", "wheat", "cotton", 
            "jaggery", "gur", "banana", "potato", "brinjal", "chilli", 
            "turmeric", "ginger", "soyabean", "soybean", "mustard", 
            "maize", "corn", "paddy", "sugarcane"
        ]
        
        # Location templates
        self.location_templates = [
            "tamil nadu", "punjab", "maharashtra", "kerala", "karnataka",
            "andhra pradesh", "telangana", "uttar pradesh", "bihar",
            "chennai", "madurai", "coimbatore"
        ]
    
    def extract_intent_semantic(self, query: str) -> Dict[str, float]:
        """Extract intent using semantic similarity"""
        if not self.model:
            return {}
        
        try:
            query_embedding = self.model.encode([query.lower()])[0]
            intent_scores = {}
            
            for intent, templates in self.intent_templates.items():
                # Generate template embeddings (simplified - use generic placeholders)
                template_texts = [t.replace("{commodity}", "X").replace("{location}", "Y")
                                 .replace("{pest}", "Z").replace("{disease}", "D")
                                 .replace("{crop}", "C").replace("{commodity2}", "X2")
                                 for t in templates[:5]]  # Use top 5 templates
                
                template_embeddings = self.model.encode(template_texts)
                # Cosine similarity
                similarities = np.dot(template_embeddings, query_embedding) / (
                    np.linalg.norm(template_embeddings, axis=1) * np.linalg.norm(query_embedding)
                )
                intent_scores[intent] = float(np.max(similarities))
            
            return intent_scores
        except Exception as e:
            logger.warning(f"Semantic intent extraction failed: {e}")
            return {}
    
    def validate_commodity_semantic(self, candidate: str, query: str) -> float:
        """Validate if a commodity candidate is semantically related to the query"""
        if not self.model or not candidate:
            return 0.5  # Neutral score if semantic not available
        
        try:
            # Create a query that mentions the commodity
            commodity_query = f"price of {candidate.lower()}"
            query_embedding = self.model.encode([query.lower()])[0]
            commodity_embedding = self.model.encode([commodity_query])[0]
            
            similarity = np.dot(query_embedding, commodity_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(commodity_embedding)
            )
            return float(similarity)
        except Exception:
            return 0.5
    
    def refine_entities_semantic(self, query: str, keyword_entities: List[str], intent: str) -> List[str]:
        """Refine entity list using semantic validation"""
        if not self.model or not keyword_entities:
            return keyword_entities
        
        try:
            validated = []
            for entity in keyword_entities:
                # Check if entity is semantically relevant
                if intent == "market_price":
                    score = self.validate_commodity_semantic(entity, query)
                    # Threshold: 0.4 for inclusion
                    if score > 0.4:
                        validated.append(entity)
                        logger.debug(f"Entity '{entity}' validated with score {score:.2f}")
                    else:
                        logger.debug(f"Entity '{entity}' filtered out (score {score:.2f})")
                else:
                    validated.append(entity)  # For non-market intents, keep all
            
            return validated
        except Exception as e:
            logger.warning(f"Semantic entity refinement failed: {e}")
            return keyword_entities

# Global semantic extractor instance
semantic_extractor = SemanticExtractor()

