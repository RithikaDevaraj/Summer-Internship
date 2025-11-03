"""
Knowledge Graph Integration Module
Integrates fertilizer predictions with Neo4j KG
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from neo4j import GraphDatabase
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FertilizerKGIntegration:
    """Integrate fertilizer recommendations with Neo4j KG"""
    
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
            )
            # Test connection
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                session.run("RETURN 1")
            logger.info("Connected to Neo4j for fertilizer KG integration")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def upsert_fertilizer_node(self, fertilizer_name: str, properties: Dict[str, Any] = None):
        """
        Create or update a fertilizer node in KG
        
        Args:
            fertilizer_name: Name of fertilizer (e.g., "28-28", "17-17-17")
            properties: Additional properties (type, safety, cost, etc.)
        """
        try:
            if not self.driver:
                logger.warning("Neo4j driver not available")
                return False
            
            default_props = {
                "type": "NPK-based",
                "safety": "Moderate",
                "cost": "Variable",
                "last_updated": datetime.now().isoformat(),
                "source": "XGBoost_ML"
            }
            
            if properties:
                default_props.update(properties)
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MERGE (f:Fertilizer {name: $name})
                SET f += $properties
                RETURN f
                """
                session.run(query, name=fertilizer_name, properties=default_props)
                logger.debug(f"Upserted fertilizer node: {fertilizer_name}")
                return True
        
        except Exception as e:
            logger.error(f"Error upserting fertilizer node: {e}")
            return False
    
    def upsert_crop_node(self, crop_name: str, properties: Dict[str, Any] = None):
        """Create or update a crop node in KG"""
        try:
            if not self.driver:
                return False
            
            default_props = {
                "last_updated": datetime.now().isoformat(),
                "source": "XGBoost_ML"
            }
            
            if properties:
                default_props.update(properties)
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MERGE (c:Crop {name: $name})
                SET c += $properties
                RETURN c
                """
                session.run(query, name=crop_name, properties=default_props)
                logger.debug(f"Upserted crop node: {crop_name}")
                return True
        
        except Exception as e:
            logger.error(f"Error upserting crop node: {e}")
            return False
    
    def create_suitable_for_relationship(
        self,
        crop_name: str,
        fertilizer_name: str,
        score: float,
        source: str = "XGBoost",
        model_version: str = "1.0",
        additional_properties: Dict[str, Any] = None
    ):
        """
        Create or update SUITABLE_FOR relationship
        
        Args:
            crop_name: Name of crop
            fertilizer_name: Name of fertilizer
            score: Suitability score (probability)
            source: Source of recommendation
            model_version: ML model version
            additional_properties: Extra properties for relationship
        """
        try:
            if not self.driver:
                return False
            
            # Ensure nodes exist
            self.upsert_crop_node(crop_name)
            self.upsert_fertilizer_node(fertilizer_name)
            
            rel_props = {
                "score": float(score),
                "source": source,
                "model_version": model_version,
                "last_updated": datetime.now().isoformat(),
                "data_source": "Kaggle_Optimal_Fertilizers"
            }
            
            if additional_properties:
                rel_props.update(additional_properties)
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MATCH (c:Crop {name: $crop_name})
                MATCH (f:Fertilizer {name: $fertilizer_name})
                MERGE (c)-[r:SUITABLE_FOR]->(f)
                SET r += $properties
                RETURN r
                """
                session.run(query, crop_name=crop_name, fertilizer_name=fertilizer_name, properties=rel_props)
                logger.debug(f"Created SUITABLE_FOR relationship: {crop_name} -> {fertilizer_name} (score: {score})")
                return True
        
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
    
    def batch_update_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        crop_name: str,
        model_version: str = "1.0"
    ):
        """
        Batch update multiple fertilizer recommendations for a crop
        
        Args:
            recommendations: List of dicts with 'name' and 'score' keys
            crop_name: Name of crop
            model_version: ML model version
        """
        try:
            if not self.driver:
                return False
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                for rec in recommendations:
                    fertilizer_name = rec.get('name')
                    score = rec.get('score', 0.0)
                    
                    self.create_suitable_for_relationship(
                        crop_name=crop_name,
                        fertilizer_name=fertilizer_name,
                        score=score,
                        model_version=model_version
                    )
            
            logger.info(f"Batch updated {len(recommendations)} recommendations for {crop_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error batch updating recommendations: {e}")
            return False
    
    def get_fertilizer_info(self, fertilizer_names: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve fertilizer information from KG
        
        Args:
            fertilizer_names: List of fertilizer names to query
            
        Returns:
            List of fertilizer info dictionaries
        """
        try:
            if not self.driver:
                return []
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MATCH (f:Fertilizer)
                WHERE f.name IN $names
                OPTIONAL MATCH (c:Crop)-[r:SUITABLE_FOR]->(f)
                WITH f, collect(DISTINCT {crop: c.name, score: r.score}) as crops
                RETURN f.name as name,
                       f.type as type,
                       f.safety as safety,
                       f.cost as cost,
                       f.composition as composition,
                       f.usage as usage,
                       f.npk_ratio as npk_ratio,
                       crops
                """
                records = session.run(query, names=fertilizer_names)
                
                results = []
                for record in records:
                    results.append({
                        'name': record['name'],
                        'type': record.get('type', 'NPK-based'),
                        'safety': record.get('safety', 'Moderate'),
                        'cost': record.get('cost', 'Variable'),
                        'composition': record.get('composition'),
                        'usage': record.get('usage'),
                        'npk_ratio': record.get('npk_ratio'),
                        'suitable_crops': [c['crop'] for c in record.get('crops', []) if c['crop']]
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Error getting fertilizer info: {e}")
            return []
    
    def compare_fertilizers_kg(self, fertilizer_names: List[str]) -> Dict[str, Any]:
        """
        Compare fertilizers by querying KG
        
        Args:
            fertilizer_names: List of fertilizer names to compare
            
        Returns:
            Comparison dictionary
        """
        try:
            fertilizers = self.get_fertilizer_info(fertilizer_names)
            
            return {
                "fertilizers": fertilizers,
                "count": len(fertilizers),
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error comparing fertilizers: {e}")
            return {"fertilizers": [], "count": 0}
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()

