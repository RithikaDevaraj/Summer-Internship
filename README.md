🌾 Prakriti - Agentic KG-RAG System for Indian Agriculture
An intelligent agricultural advisory system that combines Knowledge Graphs with Retrieval-Augmented Generation (RAG) to provide contextual, multilingual agricultural advice to Indian farmers.

🚀 Features
Knowledge Graph Integration: Neo4j AuraDB with comprehensive agricultural data
RAG Pipeline: LangChain-powered retrieval combining structured and unstructured data
Autonomous Agent: Real-time updates with pest alerts, weather events, and disease outbreaks
Interactive Chat: Natural language interface for agricultural queries
Graph Visualization: Visual exploration of agricultural knowledge relationships
Real-time Events: Live updates on agricultural conditions and alerts
🏗️ Architecture
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend │────│   FastAPI Backend │────│   Neo4j AuraDB  │
│   (Port 5173)   │    │   (Port 8000)    │    │   (Cloud)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
    ┌─────────┐              ┌─────────┐              ┌─────────┐
    │ Chat UI │              │   RAG   │              │ Knowledge│
    │ Graph   │              │Pipeline │              │  Graph   │
    │Visualiz.│              │LangChain│              │   Data   │
    └─────────┘              └─────────┘              └─────────┘
📋 Prerequisites
Node.js 18+ and pnpm
Python 3.11+
Neo4j AuraDB account (configured in .env)
OpenAI API key (for LLM functionality)
🛠️ Installation & Setup
1. Clone and Setup Frontend
# Install frontend dependencies
pnpm install

# Start frontend development server
pnpm run dev
2. Setup Backend
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Neo4j and OpenAI credentials

# Start backend server
uvicorn main:app --reload
3. Docker Setup (Alternative)
# Start all services with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
🔧 Configuration
Environment Variables
Create backend/.env with the following configuration:

# Neo4j AuraDB Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
MODEL_NAME=Prakriti

# Dataset URLs (automatically loaded)
CROP_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Crop.csv
PEST_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Pest.csv
DISEASE_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Disease.csv
CONTROL_METHOD_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/ControlMethod.csv
REGION_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Region.csv
RELATIONS_CSV_URL=https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Relations.csv
🎯 Usage
Chat Interface
Ask Questions: Type natural language queries about agriculture

“What pests affect rice in Tamil Nadu?”
“How to control cotton bollworm?”
“Best crops for monsoon season”
View Sources: Each response shows knowledge graph and document sources

Explore Graph: Click on the graph visualization to explore relationships

API Endpoints
POST /query - Process agricultural queries
GET /graph - Get graph data for visualization
GET /events - Get recent agricultural events
POST /update - Trigger manual agent updates
GET /status - Check system status
GET /search/{entity_type} - Search specific entities
Example API Usage
# Query the system
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What pests affect rice crops?"}'

# Get graph data
curl "http://localhost:8000/graph"

# Check system status
curl "http://localhost:8000/status"
🧠 System Components
1. Knowledge Graph (Neo4j)
Crops: Rice, wheat, cotton, etc. with properties
Pests: Insects and their damage patterns
Diseases: Pathogens and symptoms
Regions: Indian states and climate data
Control Methods: Pesticides and organic solutions
Relationships: Complex interconnections between entities
2. RAG Pipeline
Knowledge Graph Retrieval: Structured Cypher queries
Vector Store: FAISS with agricultural documents
LLM Integration: OpenAI GPT for response generation
Context Fusion: Combines structured and unstructured data
3. Autonomous Agent
Pest Alerts: Simulated pest outbreak notifications
Weather Events: Rainfall, drought, and storm alerts
Disease Outbreaks: Pathogen spread notifications
Scheduled Updates: Automatic data refresh every few hours
4. Frontend Interface
React Components: Modern UI with Tailwind CSS
Real-time Chat: Interactive conversation interface
Graph Visualization: D3-powered network visualization
Event Dashboard: Live agricultural event monitoring
🔄 Data Flow
User Query → Frontend captures natural language input
API Request → Sent to FastAPI backend
Knowledge Extraction → Extract entities and keywords
Graph Query → Cypher queries to Neo4j for structured data
Vector Search → FAISS similarity search for documents
Context Fusion → Combine graph and document results
LLM Generation → OpenAI generates contextual response
Response Display → Frontend shows answer with sources
🧪 Testing
Backend Testing
cd backend
python -m pytest tests/
Frontend Testing
pnpm test
Manual Testing
Start both frontend and backend
Open http://localhost:5173
Ask sample questions:
“Rice pests in Tamil Nadu”
“Wheat diseases in Punjab”
“Cotton farming in Maharashtra”
📊 Monitoring
System Status
Neo4j Connection: Database connectivity status
Agent Status: Autonomous update process status
Recent Events: Latest agricultural alerts and updates
Performance Metrics
Response Time: Query processing duration
Knowledge Graph Hits: Successful entity retrievals
Vector Store Hits: Document similarity matches
🚀 Deployment
Production Deployment
Environment Setup

# Set production environment variables
export NODE_ENV=production
export API_URL=https://your-api-domain.com
Build Frontend

pnpm run build
Deploy Backend

# Use production WSGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
Docker Production

docker-compose -f docker-compose.prod.yml up -d
🤝 Contributing
Fork the repository
Create feature branch (git checkout -b feature/amazing-feature)
Commit changes (git commit -m 'Add amazing feature')
Push to branch (git push origin feature/amazing-feature)
Open Pull Request
📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
Neo4j for graph database technology
LangChain for RAG pipeline framework
OpenAI for language model capabilities
React & Tailwind for modern frontend development
Indian Agricultural Research for domain knowledge
📞 Support
For support and questions:

Create an issue in the GitHub repository
Contact the development team
Check the API documentation at /docs
Built with ❤️ for Indian Agriculture