import numpy as np
from typing import List, Dict, Any, Optional
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.schema import Document
import logging
from config import config
from kg_connector import neo4j_connector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.llm = None
        self.qa_chain = None
        self.initialize_components()
    
    def initialize_components(self):
        """Initialize RAG pipeline components"""
        try:
            # Initialize OpenAI embeddings
            if config.OPENAI_API_KEY:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=config.OPENAI_API_KEY
                )
                self.llm = OpenAI(
                    openai_api_key=config.OPENAI_API_KEY,
                    temperature=0.7,
                    max_tokens=500
                )
                logger.info("OpenAI components initialized successfully")
            else:
                logger.warning("OpenAI API key not found, using mock components")
                self.embeddings = MockEmbeddings()
                self.llm = MockLLM()
            
            # Initialize FAISS vector store (stub for now)
            self.initialize_vector_store()
            
        except Exception as e:
            logger.error(f"Error initializing RAG components: {e}")
            # Fallback to mock components
            self.embeddings = MockEmbeddings()
            self.llm = MockLLM()
            self.initialize_vector_store()
    
    def initialize_vector_store(self):
        """Initialize FAISS vector store with agricultural documents"""
        try:
            # Create sample agricultural documents for demonstration
            sample_docs = [
                Document(
                    page_content="Rice is a staple crop in India, primarily grown in Tamil Nadu, West Bengal, and Punjab. It requires abundant water and is susceptible to pests like stem borer and brown planthopper.",
                    metadata={"source": "agricultural_guide", "crop": "rice", "region": "india"}
                ),
                Document(
                    page_content="Wheat cultivation in Punjab and Haryana follows the Rabi season. Common diseases include rust and smut. Proper irrigation and fertilization are crucial for good yield.",
                    metadata={"source": "agricultural_guide", "crop": "wheat", "region": "north_india"}
                ),
                Document(
                    page_content="Cotton bollworm is a major pest affecting cotton crops across Maharashtra and Gujarat. Integrated pest management using biological and chemical controls is recommended.",
                    metadata={"source": "pest_management", "crop": "cotton", "pest": "bollworm"}
                ),
                Document(
                    page_content="Organic farming methods include crop rotation, composting, and biological pest control. These methods are sustainable and environmentally friendly.",
                    metadata={"source": "organic_farming", "type": "sustainable_agriculture"}
                ),
                Document(
                    page_content="Monsoon patterns significantly affect agricultural productivity in India. Delayed monsoons can lead to drought conditions affecting crop yields.",
                    metadata={"source": "weather_agriculture", "factor": "monsoon"}
                )
            ]
            
            # Create FAISS vector store
            if self.embeddings:
                self.vector_store = FAISS.from_documents(
                    documents=sample_docs,
                    embedding=self.embeddings
                )
                logger.info("FAISS vector store initialized with sample documents")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            self.vector_store = None
    
    def retrieve_from_kg(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve structured data from Knowledge Graph"""
        try:
            kg_results = neo4j_connector.query_knowledge_graph(query)
            logger.info(f"Retrieved {len(kg_results)} results from Knowledge Graph")
            return kg_results
        except Exception as e:
            logger.error(f"Error retrieving from Knowledge Graph: {e}")
            return []
    
    def retrieve_from_vector_store(self, query: str, k: int = 3) -> List[Document]:
        """Retrieve similar documents from FAISS vector store"""
        try:
            if self.vector_store:
                docs = self.vector_store.similarity_search(query, k=k)
                logger.info(f"Retrieved {len(docs)} documents from vector store")
                return docs
            else:
                logger.warning("Vector store not initialized")
                return []
        except Exception as e:
            logger.error(f"Error retrieving from vector store: {e}")
            return []
    
    def combine_contexts(self, kg_results: List[Dict], vector_docs: List[Document], query: str) -> str:
        """Combine Knowledge Graph and vector store results into context"""
        context_parts = []
        
        # Add Knowledge Graph structured data
        if kg_results:
            context_parts.append("=== Knowledge Graph Data ===")
            for result in kg_results[:5]:  # Limit to top 5 results
                if 'data' in result and 'name' in result:
                    data = result['data']
                    context_parts.append(f"{result['type'].title()}: {result['name']}")
                    
                    # Add relevant properties
                    for key, value in data.items():
                        if key not in ['id', 'name'] and value:
                            context_parts.append(f"  - {key}: {value}")
                    context_parts.append("")
        
        # Add vector store unstructured data
        if vector_docs:
            context_parts.append("=== Related Information ===")
            for doc in vector_docs:
                context_parts.append(f"- {doc.page_content}")
                if doc.metadata:
                    metadata_str = ", ".join([f"{k}: {v}" for k, v in doc.metadata.items()])
                    context_parts.append(f"  Source: {metadata_str}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def generate_response(self, query: str, context: str) -> str:
        """Generate response using LLM with combined context"""
        try:
            prompt = f"""
You are Prakriti, an AI agricultural advisor for Indian farmers. Based on the provided context, answer the farmer's question with practical, actionable advice.

Context:
{context}

Question: {query}

Instructions:
1. Provide specific, practical advice relevant to Indian agriculture
2. Include information about crops, pests, diseases, or regions if mentioned in the context
3. Suggest control methods or solutions when applicable
4. Keep the response concise but informative
5. If the context doesn't contain relevant information, provide general agricultural guidance

Answer:"""

            if hasattr(self.llm, 'predict'):
                response = self.llm.predict(prompt)
            else:
                # Mock response for testing
                response = self.generate_mock_response(query, context)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self.generate_mock_response(query, context)
    
    def generate_mock_response(self, query: str, context: str) -> str:
        """Generate a mock response for testing when OpenAI is not available"""
        query_lower = query.lower()
        
        if "rice" in query_lower and "pest" in query_lower:
            return """Based on the agricultural data, rice crops are commonly affected by pests like stem borer and brown planthopper. Here are recommended control measures:

1. **Biological Control**: Use natural predators and parasites
2. **Cultural Practices**: Maintain proper water levels and field sanitation
3. **Chemical Control**: Apply appropriate pesticides during early infestation stages
4. **Integrated Pest Management**: Combine multiple control methods for best results

For specific regions like Tamil Nadu, monitor fields regularly during the growing season and consult local agricultural extension services for region-specific advice."""
        
        elif "wheat" in query_lower:
            return """Wheat cultivation requires careful attention to several factors:

1. **Sowing Time**: Plant during Rabi season (October-December)
2. **Irrigation**: Ensure adequate water supply, especially during grain filling
3. **Disease Management**: Watch for rust and smut diseases
4. **Fertilization**: Apply balanced NPK fertilizers based on soil testing

For regions like Punjab and Haryana, follow recommended varieties and agricultural practices for optimal yield."""
        
        elif "cotton" in query_lower:
            return """Cotton farming considerations:

1. **Pest Management**: Bollworm is a major concern - use IPM strategies
2. **Soil Preparation**: Ensure well-drained, fertile soil
3. **Water Management**: Cotton requires moderate irrigation
4. **Harvesting**: Pick cotton when bolls are fully mature

Maharashtra and Gujarat have specific guidelines for cotton cultivation that should be followed."""
        
        else:
            return f"""Thank you for your agricultural query about "{query}". Based on the available information:

1. **General Advice**: Follow integrated farming practices combining traditional knowledge with modern techniques
2. **Pest Management**: Use IPM strategies for sustainable pest control
3. **Soil Health**: Maintain soil fertility through organic matter and balanced fertilization
4. **Water Management**: Optimize irrigation based on crop requirements and local conditions

For specific guidance, consult your local agricultural extension officer or krishi vigyan kendra."""
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Main method to process user query through RAG pipeline"""
        try:
            # Step 1: Retrieve from Knowledge Graph
            kg_results = self.retrieve_from_kg(query)
            
            # Step 2: Retrieve from Vector Store
            vector_docs = self.retrieve_from_vector_store(query)
            
            # Step 3: Combine contexts
            combined_context = self.combine_contexts(kg_results, vector_docs, query)
            
            # Step 4: Generate response
            response = self.generate_response(query, combined_context)
            
            # Return structured result
            return {
                "query": query,
                "response": response,
                "kg_results": len(kg_results),
                "vector_results": len(vector_docs),
                "context_used": bool(combined_context.strip()),
                "sources": {
                    "knowledge_graph": [r.get('name', 'Unknown') for r in kg_results[:3]],
                    "documents": [d.metadata.get('source', 'Unknown') for d in vector_docs[:3]]
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "query": query,
                "response": f"I apologize, but I encountered an error processing your query. Please try rephrasing your question or contact support.",
                "kg_results": 0,
                "vector_results": 0,
                "context_used": False,
                "sources": {"knowledge_graph": [], "documents": []},
                "error": str(e)
            }

class MockEmbeddings:
    """Mock embeddings for testing without OpenAI API"""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 1536 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1536

class MockLLM:
    """Mock LLM for testing without OpenAI API"""
    def predict(self, prompt: str) -> str:
        return "This is a mock response for testing purposes."

# Global RAG pipeline instance
rag_pipeline = RAGPipeline()