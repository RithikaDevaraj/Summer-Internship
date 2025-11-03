import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Network, RefreshCw, Maximize2, Info } from 'lucide-react';
import { apiClient } from '../api/api';
import Loader from './Loader';

const GraphView = () => {
  const [graphData, setGraphData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [neighborGraph, setNeighborGraph] = useState(null);
  const maxNodes = 80;
  const maxLinks = 160;

  const mergeGraphs = (base, add) => {
    if (!base) return add;
    const nodeMap = new Map();
    base.nodes.forEach((n) => nodeMap.set(n.id || n.name, n));
    add.nodes.forEach((n) => nodeMap.set(n.id || n.name, n));
    const nodes = Array.from(nodeMap.values()).slice(0, maxNodes);
    const linkKey = (l) => `${l.source}->${l.target}:${l.relationship}`;
    const linkMap = new Map();
    base.links.forEach((l) => linkMap.set(linkKey(l), l));
    add.links.forEach((l) => linkMap.set(linkKey(l), l));
    const links = Array.from(linkMap.values()).slice(0, maxLinks);
    return { nodes, links };
  };

  const fetchNeighbors = async (name, limit = 24) => {
    const data = await apiClient.getGraphNeighbors(name, limit);
    setNeighborGraph((prev) => mergeGraphs(prev, data));
  };
  const [events, setEvents] = useState([]);
  const svgRef = useRef(null);
  // Category browser (3 at a time) and active filter
  const [categories, setCategories] = useState([]);
  const [catPageIndex, setCatPageIndex] = useState(0);
  const [activeCategory, setActiveCategory] = useState('crop');
  const catsPageSize = 3;

  useEffect(() => {
    loadGraphData();
    loadRecentEvents();
  }, []);

  useEffect(() => {
    // Build categories dynamically from graph data
    if (!graphData?.nodes) return;
    const specialNamesToKey = {
      livemarketprice: { key: 'livemarketprice', label: 'LiveMarketPrice', color: '#16A34A' },
      liveweatherdata: { key: 'liveweatherdata', label: 'LiveWeatherData', color: '#06B6D4' },
      pestalert: { key: 'pestalert', label: 'PestAlert', color: '#22D3EE' },
      weatherevent: { key: 'weatherevent', label: 'WeatherEvent', color: '#60A5FA' },
      governmentscheme: { key: 'governmentscheme', label: 'GovernmentScheme', color: '#FCA5A5' },
      diseaseoutbreak: { key: 'diseaseoutbreak', label: 'DiseaseOutbreak', color: '#A3E635' },
      marketprice: { key: 'marketprice', label: 'MarketPrice', color: '#34D399' },
      weatherdata: { key: 'weatherdata', label: 'WeatherData', color: '#93C5FD' },
    };
    const colorFor = (t) => ({
      crop: '#10B981',
      pest: '#EF4444',
      disease: '#F59E0B',
      region: '#3B82F6',
      controlmethod: '#8B5CF6',
    }[t] || '#6B7280');

    const setKeys = new Map();
    graphData.nodes.forEach((n) => {
      const t = (n.type || '').toLowerCase();
      const nameKey = (n.name || '').toLowerCase().replace(/\s+/g, '');
      const special = specialNamesToKey[nameKey];
      const key = special ? special.key : t;
      const label = special ? special.label : (t ? t.charAt(0).toUpperCase() + t.slice(1) : 'Node');
      const color = special ? special.color : colorFor(t);
      if (!key) return;
      // Ignore synthetic live data hub node/type
      if (t === 'live_data' || nameKey === 'livedatahub') return;
      // Exclude only WeatherData and MarketPrice as requested
      if (key === 'weatherdata' || key === 'marketprice') return;
      if (!setKeys.has(key)) setKeys.set(key, { key, label, color });
    });
    const cats = Array.from(setKeys.values());
    setCategories(cats);
    if (cats.length && !cats.find((c) => c.key === activeCategory)) {
      setActiveCategory(cats[0].key);
    }
  }, [graphData]);

  const loadGraphData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await apiClient.getGraphData();
      setGraphData(data);
    } catch (err) {
      console.error('Error loading graph data:', err);
      setError('Failed to load graph data. Please ensure the backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadRecentEvents = async () => {
    try {
      const data = await apiClient.getRecentEvents();
      setEvents(data.events || []);
    } catch (err) {
      console.error('Error loading events:', err);
    }
  };

  const renderSimpleGraph = () => {
    if (!graphData || !graphData.nodes) return null;

    const width = 400;
    const height = 300;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 100;

    // If neighborhood is loaded, render connected view
    if (neighborGraph && selectedNode) {
      const centerName = selectedNode.name;
      const nodes = neighborGraph.nodes;
      const center = nodes.find((n) => n.name === centerName) || { name: centerName, type: selectedNode.type };
      const neighbors = nodes.filter((n) => n.name !== centerName);
      const placed = [
        { ...center, x: centerX, y: centerY },
        ...neighbors.map((n, i) => {
          const angle = (i * 2 * Math.PI) / Math.max(1, neighbors.length);
          return { ...n, x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) };
        }),
      ];
      const getNodeColor = (type) => ({
        crop: '#10B981', pest: '#EF4444', disease: '#F59E0B', region: '#3B82F6', controlmethod: '#8B5CF6',
        governmentscheme: '#FCA5A5', diseaseoutbreak: '#A3E635', pestalert: '#22D3EE', weatherevent: '#60A5FA', liveweatherdata: '#06B6D4', livemarketprice: '#16A34A',
      }[(type || '').toLowerCase()] || '#6B7280');

      return (
        <svg ref={svgRef} width={width} height={height} className="border rounded">
          {neighborGraph.links.map((l, idx) => {
            const s = placed.find((n) => n.id === l.source || n.name === l.source);
            const t = placed.find((n) => n.id === l.target || n.name === l.target);
            if (!s || !t) return null;
            return <line key={idx} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#E5E7EB" strokeWidth="1.5" />;
          })}
          {placed.map((n) => (
            <g key={n.id || n.name}>
              <circle cx={n.x} cy={n.y} r="12" fill={getNodeColor(n.type)} stroke="#fff" strokeWidth="2" className="cursor-pointer hover:opacity-80" onClick={() => { setSelectedNode(n); fetchNeighbors(n.name, 24); }} />
              <text x={n.x} y={n.y + 20} textAnchor="middle" className="text-xs fill-gray-600 pointer-events-none">
                {(n.name || '').length > 12 ? (n.name || '').slice(0, 12) + '…' : (n.name || '')}
              </text>
            </g>
          ))}
        </svg>
      );
    }

    // Filter by active category and exclude only WeatherData/MarketPrice
    const specialNamesToKey = {
      livemarketprice: 'livemarketprice',
      liveweatherdata: 'liveweatherdata',
      pestalert: 'pestalert',
      weatherevent: 'weatherevent',
      governmentscheme: 'governmentscheme',
      diseaseoutbreak: 'diseaseoutbreak',
      marketprice: 'marketprice',
      weatherdata: 'weatherdata',
    };
    const filtered = graphData.nodes.filter((n) => {
      const t = (n.type || '').toLowerCase();
      const nameKey = (n.name || '').toLowerCase().replace(/\s+/g, '');
      const derived = specialNamesToKey[nameKey] || t;
      if (derived === 'weatherdata' || derived === 'marketprice') return false;
      return derived === activeCategory;
    });

    // Position nodes in a circle (cap to 12 for readability)
    const nodes = filtered.slice(0, 12).map((node, index) => {
      const angle = (index * 2 * Math.PI) / Math.min(graphData.nodes.length, 12);
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    const getNodeColor = (type) => {
      const colors = {
        crop: '#10B981',
        pest: '#EF4444',
        disease: '#F59E0B',
        region: '#3B82F6',
        controlmethod: '#8B5CF6',
      };
      return colors[type.toLowerCase()] || '#6B7280';
    };

    return (
      <svg ref={svgRef} width={width} height={height} className="border rounded">
        {/* Render links */}
        {graphData.links.map((link, index) => {
          const sourceNode = nodes.find(n => n.id === link.source);
          const targetNode = nodes.find(n => n.id === link.target);
          
          if (!sourceNode || !targetNode) return null;
          
          return (
            <line
              key={index}
              x1={sourceNode.x}
              y1={sourceNode.y}
              x2={targetNode.x}
              y2={targetNode.y}
              stroke="#E5E7EB"
              strokeWidth="1"
              opacity="0.6"
            />
          );
        })}
        
        {/* Render nodes */}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r="12"
              fill={getNodeColor(node.type)}
              stroke="#fff"
              strokeWidth="2"
              className="cursor-pointer hover:opacity-80"
              onClick={() => setSelectedNode(node)}
            />
            <text
              x={node.x}
              y={node.y + 20}
              textAnchor="middle"
              className="text-xs fill-gray-600 pointer-events-none"
            >
              {node.name.length > 10 ? node.name.substring(0, 10) + '...' : node.name}
            </text>
          </g>
        ))}
      </svg>
    );
  };

  const formatEventTime = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getEventIcon = (eventType) => {
    switch (eventType?.toLowerCase()) {
      case 'pestalert':
        return '🐛';
      case 'weatherevent':
        return '🌤️';
      case 'diseaseoutbreak':
        return '🦠';
      default:
        return '📢';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <Loader text="Loading knowledge graph..." />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Network className="w-5 h-5" />
            <span>Knowledge Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center h-full space-y-4">
          <p className="text-red-600 text-center">{error}</p>
          <Button onClick={loadGraphData} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-blue-600" />
          <span>Knowledge Graph</span>
        </CardTitle>
        
        {graphData && (
          <div className="flex space-x-4 text-sm text-gray-600">
            <span>Nodes: {graphData.stats?.total_nodes || 0}</span>
            <span>Links: {graphData.stats?.total_relationships || 0}</span>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col p-0">
        {/* Graph Visualization */}
        <div className="px-4 pb-2">
          <div className="flex justify-center bg-gray-50 rounded-lg p-4">
            {renderSimpleGraph()}
          </div>
          
          {/* Category slider (controls node types) */}
          {categories.length > 0 && (() => {
            const totalPages = Math.ceil(categories.length / catsPageSize) || 1;
            const safePage = ((catPageIndex % totalPages) + totalPages) % totalPages;
            const slice = categories.slice(safePage * catsPageSize, safePage * catsPageSize + catsPageSize);
            return (
              <div className="mt-3 flex items-center justify-center gap-2">
                <button
                  aria-label="Previous categories"
                  className="px-2 py-1 border rounded hover:bg-gray-50"
                  onClick={() => setCatPageIndex((p) => (p - 1 + totalPages) % totalPages)}
                >
                  ‹
                </button>
                {slice.map((c) => (
                  <button
                    key={c.key}
                    className={`px-3 py-1 border rounded-full text-sm hover:bg-gray-50 ${activeCategory === c.key ? 'bg-gray-100' : ''}`}
                    onClick={() => setActiveCategory(c.key)}
                  >
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-2"
                      style={{ backgroundColor: c.color }}
                    />
                    {c.label}
                  </button>
                ))}
                <button
                  aria-label="Next categories"
                  className="px-2 py-1 border rounded hover:bg-gray-50"
                  onClick={() => setCatPageIndex((p) => (p + 1) % totalPages)}
                >
                  ›
                </button>
              </div>
            );
          })()}
        </div>
        
        <Separator />
        
        {/* Node Details or Recent Events */}
        <div className="flex-1 px-4 py-2">
          {selectedNode ? (
            <div>
              <h3 className="font-semibold mb-2 flex items-center">
                <Info className="w-4 h-4 mr-2" />
                {selectedNode.name}
              </h3>
              <Badge className="mb-2">{selectedNode.type}</Badge>
              
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div className="space-y-1">
                  {Object.entries(selectedNode.properties).map(([key, value]) => (
                    value && (
                      <div key={key} className="text-sm">
                        <span className="font-medium capitalize">{key.replace('_', ' ')}: </span>
                        <span className="text-gray-600">{value}</span>
                      </div>
                    )
                  ))}
                </div>
              )}
              
              <div className="flex gap-2 mt-2">
                <Button 
                onClick={() => setSelectedNode(null)} 
                variant="outline" 
                size="sm" 
              >
                Close
                </Button>
                <Button onClick={() => fetchNeighbors(selectedNode.name, 24)} size="sm">Show neighbors</Button>
                <Button
                  onClick={async () => {
                    try {
                      // First hop
                      await fetchNeighbors(selectedNode.name, 24);
                      // Second hop: expand a few neighbors
                      const expandFrom = (neighborGraph?.nodes || []).filter((n) => n.name !== selectedNode.name).slice(0, 6);
                      for (const n of expandFrom) {
                        await fetchNeighbors(n.name, 16);
                      }
                    } catch (e) {
                      console.error('2-hop expansion error', e);
                    }
                  }}
                  size="sm"
                  variant="outline"
                >
                  Expand 2 hops
                </Button>
                {neighborGraph && (
                  <Button size="sm" variant="outline" onClick={() => setNeighborGraph(null)}>
                    Clear neighbors
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div>
              <h3 className="font-semibold mb-2">Recent Events ({events.length})</h3>
              <ScrollArea className="h-48">
                <div className="space-y-2">
                  {events.length > 0 ? (
                    events.map((event, index) => (
                      <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">
                            {getEventIcon(event.event_type)} {event.name}
                          </span>
                          {event.severity && (
                            <Badge className={`text-xs ${getSeverityColor(event.severity)}`}>
                              {event.severity}
                            </Badge>
                          )}
                        </div>
                        
                        {event.regions && (
                          <div className="text-gray-600">
                            Regions: {Array.isArray(event.regions) ? event.regions.join(', ') : event.regions}
                          </div>
                        )}
                        
                        {event.timestamp && (
                          <div className="text-xs text-gray-500 mt-1">
                            {formatEventTime(event.timestamp)}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-500 text-center py-4">
                      No recent events available
                    </p>
                  )}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default GraphView;