import logging
import pandas as pd
import requests
from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import os
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jConnector:
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
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
    
    def auto_load_data(self):
        """Automatically load data if database is empty"""
        try:
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                # Check if data exists
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                
                if count == 0:
                    logger.info("Database is empty, loading sample data...")
                    self.load_sample_data()
                else:
                    logger.info(f"Database contains {count} nodes")
        except Exception as e:
            logger.error(f"Error checking database: {e}")
    
    def load_sample_data(self):
        """Load sample agricultural data"""
        try:
            # Create sample nodes
            sample_data = {
                "crops": [
                    {"name": "Rice", "type": "Cereal", "season": "Kharif", "duration": "120-150 days"},
                    {"name": "Wheat", "type": "Cereal", "season": "Rabi", "duration": "120-140 days"},
                    {"name": "Cotton", "type": "Fiber", "season": "Kharif", "duration": "150-180 days"},
                    {"name": "Sugarcane", "type": "Cash Crop", "season": "Year-round", "duration": "12-18 months"},
                    {"name": "Maize", "type": "Cereal", "season": "Kharif", "duration": "90-120 days"}
                ],
                "pests": [
                    {"name": "Brown Planthopper", "type": "Insect", "damage": "Sucking pest", "crops_affected": ["Rice"]},
                    {"name": "Cotton Bollworm", "type": "Insect", "damage": "Fruit borer", "crops_affected": ["Cotton"]},
                    {"name": "Aphids", "type": "Insect", "damage": "Sucking pest", "crops_affected": ["Wheat", "Cotton"]},
                    {"name": "Whitefly", "type": "Insect", "damage": "Sucking pest", "crops_affected": ["Cotton"]},
                    {"name": "Stem Borer", "type": "Insect", "damage": "Stem borer", "crops_affected": ["Rice", "Maize"]}
                ],
                "diseases": [
                    {"name": "Blast Disease", "type": "Fungal", "symptoms": "Leaf spots", "crops_affected": ["Rice"]},
                    {"name": "Rust", "type": "Fungal", "symptoms": "Orange pustules", "crops_affected": ["Wheat"]},
                    {"name": "Bacterial Blight", "type": "Bacterial", "symptoms": "Water-soaked lesions", "crops_affected": ["Rice", "Cotton"]},
                    {"name": "Powdery Mildew", "type": "Fungal", "symptoms": "White powdery coating", "crops_affected": ["Wheat"]},
                    {"name": "Leaf Curl", "type": "Viral", "symptoms": "Curled leaves", "crops_affected": ["Cotton"]}
                ],
                "regions": [
                    {"name": "Tamil Nadu", "state": "Tamil Nadu", "climate": "Tropical", "major_crops": ["Rice", "Cotton", "Sugarcane"]},
                    {"name": "Punjab", "state": "Punjab", "climate": "Semi-arid", "major_crops": ["Wheat", "Rice", "Maize"]},
                    {"name": "Maharashtra", "state": "Maharashtra", "climate": "Tropical", "major_crops": ["Cotton", "Sugarcane", "Rice"]},
                    {"name": "Kerala", "state": "Kerala", "climate": "Tropical", "major_crops": ["Rice", "Coconut", "Spices"]},
                    {"name": "Karnataka", "state": "Karnataka", "climate": "Tropical", "major_crops": ["Rice", "Cotton", "Sugarcane"]}
                ],
                "control_methods": [
                    {"name": "Neem Oil", "type": "Organic", "target": "Broad spectrum", "application": "Foliar spray"},
                    {"name": "Chlorpyrifos", "type": "Chemical", "target": "Sucking pests", "application": "Foliar spray"},
                    {"name": "Bacillus thuringiensis", "type": "Biological", "target": "Caterpillars", "application": "Foliar spray"},
                    {"name": "Copper Fungicide", "type": "Chemical", "target": "Fungal diseases", "application": "Foliar spray"},
                    {"name": "Crop Rotation", "type": "Cultural", "target": "General", "application": "Field practice"}
                ]
            }
            
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                # Create nodes
                for node_type, nodes in sample_data.items():
                    for node in nodes:
                        query = f"CREATE (n:{node_type.title()}) SET n += $properties"
                        session.run(query, properties=node)
                
                # Create relationships
                relationships = [
                    # Crop-Pest relationships
                    ("Rice", "Brown Planthopper", "AFFECTED_BY"),
                    ("Cotton", "Cotton Bollworm", "AFFECTED_BY"),
                    ("Wheat", "Aphids", "AFFECTED_BY"),
                    ("Cotton", "Whitefly", "AFFECTED_BY"),
                    ("Rice", "Stem Borer", "AFFECTED_BY"),
                    
                    # Crop-Disease relationships
                    ("Rice", "Blast Disease", "AFFECTED_BY"),
                    ("Wheat", "Rust", "AFFECTED_BY"),
                    ("Rice", "Bacterial Blight", "AFFECTED_BY"),
                    ("Cotton", "Bacterial Blight", "AFFECTED_BY"),
                    ("Wheat", "Powdery Mildew", "AFFECTED_BY"),
                    ("Cotton", "Leaf Curl", "AFFECTED_BY"),
                    
                    # Region-Crop relationships
                    ("Tamil Nadu", "Rice", "GROWS"),
                    ("Tamil Nadu", "Cotton", "GROWS"),
                    ("Punjab", "Wheat", "GROWS"),
                    ("Punjab", "Rice", "GROWS"),
                    ("Maharashtra", "Cotton", "GROWS"),
                    ("Maharashtra", "Sugarcane", "GROWS"),
                    
                    # Control-Pest relationships
                    ("Neem Oil", "Brown Planthopper", "CONTROLS"),
                    ("Chlorpyrifos", "Cotton Bollworm", "CONTROLS"),
                    ("Neem Oil", "Aphids", "CONTROLS"),
                    ("Chlorpyrifos", "Whitefly", "CONTROLS"),
                    
                    # Control-Disease relationships
                    ("Copper Fungicide", "Blast Disease", "CONTROLS"),
                    ("Copper Fungicide", "Rust", "CONTROLS"),
                    ("Copper Fungicide", "Bacterial Blight", "CONTROLS"),
                    ("Copper Fungicide", "Powdery Mildew", "CONTROLS")
                ]
                
                for source, target, relationship in relationships:
                    query = f"""
                    MATCH (a), (b)
                    WHERE a.name = $source AND b.name = $target
                    CREATE (a)-[r:{relationship}]->(b)
                    """
                    session.run(query, source=source, target=target)
                
                logger.info("Sample data loaded successfully")
                
        except Exception as e:
            logger.error(f"Error loading sample data: {e}")
    
    def get_sample_nodes(self, limit: int = 20) -> Dict[str, List[Dict]]:
        """Get sample nodes for visualization"""
        try:
            result = {}
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                # Get nodes by type
                node_types = ["Crop", "Pest", "Disease", "Region", "Controlmethod"]
                
                for node_type in node_types:
                    query = f"MATCH (n:{node_type}) RETURN n LIMIT {limit // len(node_types)}"
                    records = session.run(query)
                    result[node_type.lower()] = [dict(record["n"]) for record in records]
            
            return result
        except Exception as e:
            logger.error(f"Error getting sample nodes: {e}")
            return {}
    
    def get_sample_relationships(self, limit: int = 30) -> List[Dict]:
        """Get sample relationships for visualization"""
        try:
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MATCH (a)-[r]->(b)
                RETURN a.name as source_name, 
                       b.name as target_name, 
                       type(r) as relationship_type
                LIMIT $limit
                """
                records = session.run(query, limit=limit)
                return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Error getting sample relationships: {e}")
            return []
    
    def search_entities(self, entity_type: str, search_term: str = "") -> List[Dict]:
        """Search for entities in the knowledge graph"""
        try:
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                if search_term:
                    query = f"""
                    MATCH (n:{entity_type.title()})
                    WHERE toLower(n.name) CONTAINS toLower($search_term)
                    RETURN n
                    LIMIT 20
                    """
                    records = session.run(query, search_term=search_term)
                else:
                    query = f"MATCH (n:{entity_type.title()}) RETURN n LIMIT 20"
                    records = session.run(query)
                
                return [dict(record["n"]) for record in records]
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    def get_related_entities(self, entity_name: str, relationship_type: str = None) -> Dict[str, List[Dict]]:
        """Get entities related to a specific entity"""
        try:
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                if relationship_type:
                    query = """
                    MATCH (a)-[r]->(b)
                    WHERE a.name = $entity_name AND type(r) = $relationship_type
                    RETURN b, type(r) as relationship_type
                    """
                    records = session.run(query, entity_name=entity_name, relationship_type=relationship_type)
                else:
                    query = """
                    MATCH (a)-[r]->(b)
                    WHERE a.name = $entity_name
                    RETURN b, type(r) as relationship_type
                    """
                    records = session.run(query, entity_name=entity_name)
                
                result = {}
                for record in records:
                    rel_type = record["relationship_type"]
                    if rel_type not in result:
                        result[rel_type] = []
                    result[rel_type].append(dict(record["b"]))
                
                return result
        except Exception as e:
            logger.error(f"Error getting related entities: {e}")
            return {}
    
    def search_fertilizers_pesticides(self, search_term: str = "", product_type: str = None) -> List[Dict]:
        """Search for fertilizers or pesticides"""
        try:
            with self.driver.session(database=config.NEO4J_DATABASE) as session:
                if product_type:
                    node_type = "Fertilizer" if product_type.lower() == "fertilizer" else "Pesticide"
                    if search_term:
                        query = f"""
                        MATCH (p:{node_type})
                        WHERE toLower(p.name) CONTAINS toLower($search_term)
                        RETURN p, labels(p)[0] as type
                        LIMIT 50
                        """
                        records = session.run(query, search_term=search_term)
                    else:
                        query = f"MATCH (p:{node_type}) RETURN p, labels(p)[0] as type LIMIT 50"
                        records = session.run(query)
                else:
                    if search_term:
                        query = """
                        MATCH (p)
                        WHERE (p:Fertilizer OR p:Pesticide) AND toLower(p.name) CONTAINS toLower($search_term)
                        RETURN p, labels(p)[0] as type
                        LIMIT 50
                        """
                        records = session.run(query, search_term=search_term)
                    else:
                        query = """
                        MATCH (p)
                        WHERE p:Fertilizer OR p:Pesticide
                        RETURN p, labels(p)[0] as type
                        LIMIT 50
                        """
                        records = session.run(query)
                
                results = []
                for record in records:
                    product = dict(record["p"])
                    product["product_type"] = record["type"]
                    results.append(product)
                
                return results
        except Exception as e:
            logger.error(f"Error searching fertilizers/pesticides: {e}")
            return []

# Global Neo4j connector instance
neo4j_connector = Neo4jConnector()
