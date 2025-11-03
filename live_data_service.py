import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from config import config
from kg_connector import neo4j_connector
import requests

# Open-Meteo client with caching and retry
try:
    import openmeteo_requests
    import pandas as pd
    import requests_cache
    from retry_requests import retry
except Exception:
    openmeteo_requests = None
    requests_cache = None
    retry = None
    pd = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveDataService:
    def __init__(self):
        # Open-Meteo does not require API key. We'll use city presets from config.
        self.openmeteo_client = None
        if openmeteo_requests and requests_cache and retry:
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            self.openmeteo_client = openmeteo_requests.Client(session=retry_session)

        # Agmarknet
        self.agmarknet_base = config.AGMARKNET_API_BASE
        self.agmarknet_api_key = config.AGMARKNET_API_KEY
        self.last_update = {}
    
    async def upsert_weather_for_city(self, city: str) -> Dict[str, Any]:
        """Fetch weather for a city and upsert into KG; returns processed dict."""
        data = await self.fetch_weather_data(city)
        await self._update_weather_in_kg(data)
        return data

    async def upsert_market_prices(self, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Fetch market prices and upsert into KG; returns processed list."""
        data = await self.fetch_market_prices(params)
        await self._update_market_prices_in_kg(data)
        return data
    
    async def fetch_weather_data(self, city: str) -> Dict[str, Any]:
        """Fetch live weather data for a city using Open-Meteo."""
        try:
            if not self.openmeteo_client:
                raise RuntimeError("Open-Meteo client not initialized. Ensure dependencies are installed.")

            coords = config.WEATHER_CITIES.get(city)
            if not coords:
                raise ValueError(f"Unknown city: {city}")

            lat, lon = coords
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": [lat],
                "longitude": [lon],
                "models": "gfs_global",
                "timezone": "auto",
                "past_days": 92,
                "forecast_days": 16,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "precipitation",
                    "wind_speed_10m",
                    "apparent_temperature",
                    "rain",
                    "wind_direction_10m",
                    "weather_code",
                    "cloud_cover",
                    "evapotranspiration",
                    "soil_temperature_0cm",
                    "et0_fao_evapotranspiration",
                    "soil_moisture_0_to_1cm",
                ],
            }

            responses = self.openmeteo_client.weather_api(url, params=params)
            response = responses[0]

            # Use the latest hourly values
            hourly = response.Hourly()
            def last(idx):
                arr = hourly.Variables(idx).ValuesAsNumpy()
                return float(arr[-1]) if arr is not None and len(arr) else None

            temperature = last(0)
            humidity = last(1)
            precipitation_probability = last(2)
            precipitation = last(3)
            wind_speed = last(4)
            apparent_temperature = last(5)
            rain = last(6)
            wind_direction = last(7)
            weather_code = last(8)
            cloud_cover = last(9)
            evapotranspiration = last(10)
            soil_temperature_0cm = last(11)
            et0_fao_evapotranspiration = last(12)
            soil_moisture_0_to_1cm = last(13)

            processed = {
                "region": city,
                "temperature": temperature,
                "humidity": humidity,
                "precipitation_probability": precipitation_probability,
                "precipitation": precipitation,
                "wind_speed": wind_speed,
                "apparent_temperature": apparent_temperature,
                "rain": rain,
                "wind_direction": wind_direction,
                "weather_code": weather_code,
                "cloud_cover": cloud_cover,
                "evapotranspiration": evapotranspiration,
                "soil_temperature_0cm": soil_temperature_0cm,
                "et0_fao_evapotranspiration": et0_fao_evapotranspiration,
                "soil_moisture_0_to_1cm": soil_moisture_0_to_1cm,
                "pressure": None,
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": self._assess_openmeteo_impact(
                    temperature=temperature if temperature is not None else 0.0,
                    humidity=humidity if humidity is not None else 0.0,
                    precipitation=precipitation if precipitation is not None else 0.0,
                    cloud_cover=cloud_cover if cloud_cover is not None else 0.0
                )
            }
            return processed
        except Exception as e:
            logger.error(f"Error fetching Open-Meteo weather for {city}: {e}")
            return {
                "region": city,
                "temperature": None,
                "humidity": None,
                "weather_condition": "unknown",
                "wind_speed": None,
                "pressure": None,
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": "Weather data unavailable"
            }
    
    def _assess_openmeteo_impact(self, temperature: float, humidity: float, precipitation: float, cloud_cover: float) -> str:
        """Assess agricultural impact using Open-Meteo current vars."""
        try:
            if precipitation and precipitation > 2 and humidity and humidity > 80:
                return "High fungal disease risk; ensure drainage and monitor fields."
            if temperature and temperature > 35 and humidity and humidity < 40:
                return "Heat stress risk; increase irrigation frequency."
            if temperature and temperature < 15:
                return "Cold stress risk; protect sensitive crops."
            if cloud_cover and cloud_cover > 80:
                return "Low solar radiation; adjust irrigation/fertilizer scheduling."
            return "Favorable conditions for most crops."
        except Exception:
            return "Conditions unclear; monitor field conditions."
    
    def _generate_mock_weather_data(self, region: str) -> Dict[str, Any]:
        """Generate mock weather data for demonstration"""
        import random
        
        mock_data = {
            "Tamil Nadu": {"temp": 28, "humidity": 75, "condition": "partly cloudy"},
            "Punjab": {"temp": 22, "humidity": 60, "condition": "clear sky"},
            "Maharashtra": {"temp": 30, "humidity": 70, "condition": "scattered clouds"},
            "Kerala": {"temp": 26, "humidity": 85, "condition": "light rain"},
            "Karnataka": {"temp": 25, "humidity": 68, "condition": "overcast"}
        }
        
        base_data = mock_data.get(region, {"temp": 25, "humidity": 70, "condition": "clear"})
        
        return {
            "region": region,
            "temperature": base_data["temp"] + random.randint(-3, 3),
            "humidity": base_data["humidity"] + random.randint(-10, 10),
            "weather_condition": base_data["condition"],
            "wind_speed": random.uniform(5, 15),
            "pressure": random.uniform(1010, 1020),
            "timestamp": datetime.now().isoformat(),
            "agricultural_impact": self._assess_mock_impact(base_data)
        }
    
    def _assess_agricultural_impact(self, weather_data: Dict) -> str:
        """Assess agricultural impact based on weather conditions"""
        temp = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]
        condition = weather_data["weather"][0]["main"].lower()
        
        if "rain" in condition and humidity > 80:
            return "High risk of fungal diseases. Ensure proper drainage."
        elif temp > 35 and humidity < 40:
            return "Heat stress risk for crops. Increase irrigation frequency."
        elif temp < 15:
            return "Cold stress risk. Protect sensitive crops."
        else:
            return "Favorable conditions for most crops."
    
    def _assess_mock_impact(self, data: Dict) -> str:
        """Assess agricultural impact for mock data"""
        if "rain" in data["condition"]:
            return "Good for water-intensive crops like rice. Monitor for waterlogging."
        elif data["temp"] > 30:
            return "Hot weather - ensure adequate irrigation for crops."
        else:
            return "Favorable weather conditions for agricultural activities."
    
    async def fetch_government_schemes(self) -> List[Dict[str, Any]]:
        """Disabled per request: skipping government schemes."""
        return []
    
    async def fetch_market_prices(self, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Fetch current market prices using Agmarknet (data.gov.in).
        No default geographic restriction; relies solely on provided filters.
        """
        try:
            if not self.agmarknet_api_key:
                logger.warning("AGMARKNET_API_KEY not configured; skipping market price fetch")
                return []

            query_params = {
                "api-key": self.agmarknet_api_key,
                "format": "json",
                "limit": 50,
            }

            # Only apply caller-provided filters (unrestricted by default)
            if params:
                for k, v in params.items():
                    if v:
                        query_params[k] = v

            resp = requests.get(self.agmarknet_base, params=query_params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])

            market_data: List[Dict[str, Any]] = []
            
            def to_float(val):
                try:
                    if val is None:
                        return None
                    if isinstance(val, (int, float)):
                        return float(val)
                    # clean strings like "2,400"
                    return float(str(val).replace(",", "").strip())
                except Exception:
                    return None

            from datetime import datetime as _dt
            def to_yyyy_mm_dd(dstr):
                try:
                    # Common Agmarknet format: DD/MM/YYYY
                    return _dt.strptime(dstr, "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception:
                    try:
                        return _dt.strptime(dstr, "%Y-%m-%d").strftime("%Y-%m-%d")
                    except Exception:
                        return None

            for r in records:
                date_norm = to_yyyy_mm_dd(r.get("arrival_date")) if r.get("arrival_date") else None
                market_data.append({
                    "state": r.get("state") or r.get("state.keyword"),
                    "district": r.get("district"),
                    "commodity": r.get("commodity"),
                    "variety": r.get("variety"),
                    "grade": r.get("grade"),
                    "min_price": to_float(r.get("min_price")),
                    "max_price": to_float(r.get("max_price")),
                    "price": to_float(r.get("modal_price")),
                    "unit": "quintal",
                    "market": r.get("market"),
                    "date": date_norm,
                    "trend": None,
                    "change_percent": None,
                })

            logger.info(f"Fetched {len(market_data)} market price records")
            return market_data
        except Exception as e:
            logger.error(f"Error fetching market prices: {e}")
            return []
    
    async def update_knowledge_graph_with_live_data(self):
        """Update Neo4j knowledge graph with live data"""
        try:
            # Weather: Chennai, Madurai, Coimbatore only (per request)
            cities = ["Chennai", "Madurai", "Coimbatore"]
            for city in cities:
                weather_data = await self.fetch_weather_data(city)
                await self._update_weather_in_kg(weather_data)
            
            # Market prices: default TN/Chennai or as configured later by callers
            market_prices = await self.fetch_market_prices()
            await self._update_market_prices_in_kg(market_prices)
            
            self.last_update["live_data"] = datetime.now()
            logger.info("Knowledge graph updated with live data")
            
        except Exception as e:
            logger.error(f"Error updating KG with live data: {e}")
    
    async def _update_weather_in_kg(self, weather_data: Dict):
        """Update weather information in knowledge graph"""
        try:
            with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                query = """
                MERGE (w:LiveWeatherData {region: $region, date: date()})
                SET w.temperature = $temperature,
                    w.humidity = $humidity,
                    w.precipitation_probability = $precipitation_probability,
                    w.precipitation = $precipitation,
                    w.apparent_temperature = $apparent_temperature,
                    w.rain = $rain,
                    w.wind_direction = $wind_direction,
                    w.weather_code = $weather_code,
                    w.cloud_cover = $cloud_cover,
                    w.evapotranspiration = $evapotranspiration,
                    w.soil_temperature_0cm = $soil_temperature_0cm,
                    w.et0_fao_evapotranspiration = $et0_fao_evapotranspiration,
                    w.soil_moisture_0_to_1cm = $soil_moisture_0_to_1cm,
                    w.wind_speed = $wind_speed,
                    w.pressure = $pressure,
                    w.agricultural_impact = $impact,
                    w.timestamp = datetime($timestamp)
                WITH w
                MERGE (r:Region {name: $region})
                MERGE (w)-[:FOR_REGION]->(r)
                """
                session.run(query, {
                    "region": weather_data["region"],
                    "temperature": weather_data.get("temperature"),
                    "humidity": weather_data.get("humidity"),
                    "precipitation_probability": weather_data.get("precipitation_probability"),
                    "precipitation": weather_data.get("precipitation"),
                    "apparent_temperature": weather_data.get("apparent_temperature"),
                    "rain": weather_data.get("rain"),
                    "wind_direction": weather_data.get("wind_direction"),
                    "weather_code": weather_data.get("weather_code"),
                    "cloud_cover": weather_data.get("cloud_cover"),
                    "evapotranspiration": weather_data.get("evapotranspiration"),
                    "soil_temperature_0cm": weather_data.get("soil_temperature_0cm"),
                    "et0_fao_evapotranspiration": weather_data.get("et0_fao_evapotranspiration"),
                    "soil_moisture_0_to_1cm": weather_data.get("soil_moisture_0_to_1cm"),
                    "wind_speed": weather_data.get("wind_speed"),
                    "pressure": weather_data.get("pressure"),
                    "impact": weather_data.get("agricultural_impact"),
                    "timestamp": weather_data["timestamp"]
                })
        except Exception as e:
            logger.error(f"Error updating weather in KG: {e}")
    
    async def _update_schemes_in_kg(self, schemes: List[Dict]):
        """Update government schemes in knowledge graph"""
        try:
            with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                for scheme in schemes:
                    query = """
                    MERGE (s:GovernmentScheme {name: $name})
                    SET s.description = $description,
                        s.eligibility = $eligibility,
                        s.benefit_amount = $benefit_amount,
                        s.application_link = $application_link,
                        s.last_updated = datetime($last_updated)
                    """
                    session.run(query, {
                        "name": scheme["scheme_name"],
                        "description": scheme["description"],
                        "eligibility": scheme["eligibility"],
                        "benefit_amount": scheme["benefit_amount"],
                        "application_link": scheme["application_link"],
                        "last_updated": scheme["last_updated"]
                    })
        except Exception as e:
            logger.error(f"Error updating schemes in KG: {e}")
    
    async def _update_market_prices_in_kg(self, market_data: List[Dict]):
        """Update market prices in knowledge graph"""
        try:
            with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                for item in market_data:
                    query = """
                    MERGE (m:LiveMarketPrice {commodity: $commodity, date: date($date), market: $market})
                    SET m.variety = $variety,
                        m.price = $price,
                        m.unit = $unit,
                        m.trend = $trend,
                        m.change_percent = $change_percent,
                        m.state = $state,
                        m.district = $district,
                        m.grade = $grade,
                        m.min_price = $min_price,
                        m.max_price = $max_price,
                        m.keywords = $keywords,
                        m.timestamp = datetime()
                    WITH m
                    FOREACH (_ IN CASE WHEN $state IS NOT NULL THEN [1] ELSE [] END |
                      MERGE (rs:Region {name: $state})
                      MERGE (m)-[:FOR_STATE]->(rs)
                    )
                    FOREACH (_ IN CASE WHEN $district IS NOT NULL THEN [1] ELSE [] END |
                      MERGE (rd:Region {name: $district})
                      MERGE (m)-[:FOR_DISTRICT]->(rd)
                    )
                    FOREACH (_ IN CASE WHEN $market IS NOT NULL THEN [1] ELSE [] END |
                      MERGE (rm:Region {name: $market})
                      MERGE (m)-[:FOR_MARKET]->(rm)
                    )
                    WITH m
                    CALL {
                      WITH m
                      MATCH (c:Crop {name: $commodity})
                      MERGE (m)-[:FOR_COMMODITY]->(c)
                      RETURN 0 AS _
                    }
                    RETURN m
                    """
                    session.run(query, {
                        "state": item.get("state"),
                        "district": item.get("district"),
                        "commodity": item["commodity"],
                        "variety": item["variety"],
                        "grade": item.get("grade"),
                        "min_price": item.get("min_price"),
                        "max_price": item.get("max_price"),
                        "price": item["price"],
                        "unit": item["unit"],
                        "market": item["market"],
                        "date": item["date"],
                        "trend": item["trend"],
                        "change_percent": item["change_percent"],
                        "keywords": ["Mandi", "Price", "Agriculture", "Commodity", "Market"]
                    })
        except Exception as e:
            logger.error(f"Error updating market prices in KG: {e}")
    
    async def get_live_data_summary(self) -> Dict[str, Any]:
        """Get summary of latest live data"""
        try:
            summary = {
                "weather_updates": 5,  # Number of regions updated
                "government_schemes": len(await self.fetch_government_schemes()),
                "market_commodities": len(await self.fetch_market_prices()),
                "last_update": self.last_update.get("live_data", "Never"),
                "status": "Active"
            }
            return summary
        except Exception as e:
            logger.error(f"Error getting live data summary: {e}")
            return {"status": "Error", "message": str(e)}

# Global live data service instance
live_data_service = LiveDataService()