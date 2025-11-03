import React, { useState, useEffect } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { 
  Leaf, 
  Network, 
  Settings, 
  RefreshCw, 
  Sun, 
  Moon, 
  Activity,
  AlertCircle,
  CheckCircle,
  Database,
  Scale
} from 'lucide-react';
import ChatBox from './components/ChatBox';
import GraphView from './components/GraphView';
import FertilizerPesticideModal from './components/FertilizerPesticideModal';
import { apiClient } from './api/api';

const App = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [isStatusLoading, setIsStatusLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reportContent, setReportContent] = useState(null);

  useEffect(() => {
    checkSystemStatus();
    // Check status every 30 seconds
    const interval = setInterval(checkSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkSystemStatus = async () => {
    try {
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
    } catch (error) {
      console.error('Error checking system status:', error);
      setSystemStatus({ error: 'Backend not available' });
    } finally {
      setIsStatusLoading(false);
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  const triggerUpdate = async (updateType) => {
    try {
      await apiClient.triggerUpdate(updateType);
      // Refresh status after update
      setTimeout(checkSystemStatus, 1000);
    } catch (error) {
      console.error('Error triggering update:', error);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'connected' || status === 'initialized') {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    } else {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  return (
    <TooltipProvider>
      <div className={`min-h-screen bg-gradient-to-br from-green-50 to-blue-50 ${darkMode ? 'dark' : ''}`}>
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Title */}
              <div className="flex items-center space-x-3">
                <div className="bg-green-600 p-2 rounded-lg">
                  <Leaf className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">Prakriti</h1>
                  <p className="text-sm text-gray-500">Agricultural AI Assistant</p>
                </div>
              </div>

              {/* Status and Actions */}
              <div className="flex items-center space-x-4">
                {/* Compare Fertilizers/Pesticides Button */}
                <Button
                  variant="outline"
                  onClick={() => setIsModalOpen(true)}
                  className="flex items-center space-x-2"
                >
                  <Scale className="w-4 h-4" />
                  <span>Compare Fertilizers</span>
                </Button>

                {/* System Status */}
                {systemStatus && !isStatusLoading && (
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline" className="flex items-center space-x-1">
                      <Database className="w-3 h-3" />
                      <span>Neo4j</span>
                      {getStatusIcon(systemStatus.neo4j)}
                    </Badge>
                    
                    <Badge variant="outline" className="flex items-center space-x-1">
                      <Activity className="w-3 h-3" />
                      <span>Agent</span>
                      {getStatusIcon(systemStatus.agent_updater?.running ? 'connected' : 'disconnected')}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* System Status Alert */}
          {systemStatus?.error && (
            <Card className="mb-6 border-red-200 bg-red-50">
              <CardContent className="p-4">
                <div className="flex items-center space-x-2 text-red-800">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-medium">System Status:</span>
                  <span>{systemStatus.error}</span>
                </div>
                <p className="text-sm text-red-600 mt-2">
                  Make sure the backend server is running on http://localhost:8000
                </p>
              </CardContent>
            </Card>
          )}

          {/* Optional intro removed for a more professional minimal UI */}

          {/* Main Interface */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
            {/* Chat Interface */}
            <div className="lg:col-span-2">
              <ChatBox 
                reportContent={reportContent}
                onReportReceived={() => setReportContent(null)}
              />
            </div>

            {/* Graph Visualization */}
            <div className="lg:col-span-1">
              <GraphView />
            </div>
          </div>

          {/* Fertilizer/Pesticide Modal */}
          <FertilizerPesticideModal
            open={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onReportGenerated={(report) => {
              setReportContent(report);
              setIsModalOpen(false);
            }}
          />

          {/* Removed promotional sections and footer for a cleaner, professional layout */}
        </main>
      </div>
      <Toaster />
    </TooltipProvider>
  );
};

export default App;