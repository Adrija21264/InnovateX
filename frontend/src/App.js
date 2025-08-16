import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import axios from "axios";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import { Alert, AlertDescription } from "./components/ui/alert";
import { Progress } from "./components/ui/progress";
import { Separator } from "./components/ui/separator";
import { 
  Activity, 
  Zap, 
  Code, 
  Download, 
  RefreshCw, 
  Clock, 
  TrendingUp, 
  Server,
  Database,
  Eye,
  Settings,
  AlertCircle,
  CheckCircle,
  Timer,
  Cpu,
  BarChart3
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Cold Start Prediction Dashboard Component
const ColdStartDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mockDataGenerated, setMockDataGenerated] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/dashboard`);
      setDashboardData(response.data);
      setPredictions(response.data.cold_start_system.predictions);
      
      // Also fetch detailed analytics
      const analyticsResponse = await axios.get(`${API}/jobs/analytics`);
      setAnalytics(analyticsResponse.data);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockData = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/jobs/generate-mock-data`);
      console.log("Mock data generated:", response.data);
      setMockDataGenerated(true);
      await fetchDashboardData();
    } catch (error) {
      console.error("Failed to generate mock data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return "bg-green-500";
    if (confidence >= 0.6) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getPredictionIcon = (action) => {
    return action === "prewarm" ? (
      <Zap className="h-4 w-4 text-green-600" />
    ) : (
      <Clock className="h-4 w-4 text-gray-600" />
    );
  };

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p>Loading Cold Start Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Cold Start Prediction System</h2>
          <p className="text-gray-600">AI-powered container pre-warming predictions</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={generateMockData} disabled={loading} variant="outline">
            {loading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Database className="h-4 w-4 mr-2" />}
            Generate Mock Data
          </Button>
          <Button onClick={fetchDashboardData} disabled={loading} variant="outline">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Predictions</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{predictions.length}</div>
              <p className="text-xs text-muted-foreground">
                Next 5 minutes
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Prewarm Actions</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {dashboardData.cold_start_system.active_prewarms}
              </div>
              <p className="text-xs text-muted-foreground">
                Containers to warm
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Recent Jobs</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dashboardData.cold_start_system.recent_jobs}</div>
              <p className="text-xs text-muted-foreground">
                Past 24 hours
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">Operational</span>
              </div>
              <p className="text-xs text-muted-foreground">
                All systems online
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Predictions Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Timer className="h-5 w-5" />
            <span>Live Predictions</span>
          </CardTitle>
          <CardDescription>
            Jobs predicted to run in the next 5 minutes with confidence scores
          </CardDescription>
        </CardHeader>
        <CardContent>
          {predictions.length === 0 ? (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No predictions available</p>
              <p className="text-sm text-gray-500">Generate mock data to see predictions</p>
            </div>
          ) : (
            <div className="space-y-4">
              {predictions.map((prediction, index) => (
                <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-4">
                    {getPredictionIcon(prediction.action)}
                    <div>
                      <p className="font-medium">{prediction.job_id}</p>
                      <p className="text-sm text-gray-600">{prediction.reasoning}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-sm font-medium">{prediction.predicted_run_time_window}</p>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 h-2 bg-gray-200 rounded-full">
                          <div 
                            className={`h-full rounded-full ${getConfidenceColor(prediction.confidence_score)}`}
                            style={{ width: `${prediction.confidence_score * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">
                          {(prediction.confidence_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <Badge variant={prediction.action === "prewarm" ? "default" : "secondary"}>
                      {prediction.action}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analytics Section */}
      {analytics && analytics.analytics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>Pattern Analytics</span>
            </CardTitle>
            <CardDescription>
              Historical job execution patterns and insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-3">Job Type Distribution</h4>
                <div className="space-y-2">
                  {Object.entries(analytics.analytics.job_types).map(([type, count]) => (
                    <div key={type} className="flex justify-between items-center">
                      <span className="capitalize">{type.replace('_', ' ')}</span>
                      <Badge variant="outline">{count}</Badge>
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-3">System Metrics</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span>Success Rate</span>
                    <div className="flex items-center space-x-2">
                      <Progress value={analytics.analytics.success_rate * 100} className="w-20" />
                      <span>{(analytics.analytics.success_rate * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Total Jobs Analyzed</span>
                    <Badge>{analytics.analytics.total_jobs}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Avg Prediction Confidence</span>
                    <Badge>{(analytics.summary.prediction_confidence_avg * 100).toFixed(1)}%</Badge>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// API Connector Generator Component
const ConnectorGenerator = () => {
  const [availableAPIs, setAvailableAPIs] = useState({});
  const [selectedAPI, setSelectedAPI] = useState("");
  const [generatedConnector, setGeneratedConnector] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAvailableAPIs();
  }, []);

  const fetchAvailableAPIs = async () => {
    try {
      const response = await axios.get(`${API}/connectors/available-apis`);
      setAvailableAPIs(response.data.api_specs);
    } catch (error) {
      console.error("Failed to fetch available APIs:", error);
    }
  };

  const generateConnector = async (apiName) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/connectors/${apiName}/generate`);
      setGeneratedConnector(response.data);
      setSelectedAPI(apiName);
    } catch (error) {
      console.error("Failed to generate connector:", error);
    } finally {
      setLoading(false);
    }
  };

  const downloadPackage = async (apiName) => {
    try {
      const response = await axios.get(`${API}/connectors/${apiName}/download`);
      
      // Create and download a JSON file with the package
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(response.data, null, 2));
      const downloadAnchorNode = document.createElement('a');
      downloadAnchorNode.setAttribute("href", dataStr);
      downloadAnchorNode.setAttribute("download", `${apiName}_connector_package.json`);
      document.body.appendChild(downloadAnchorNode);
      downloadAnchorNode.click();
      downloadAnchorNode.remove();
    } catch (error) {
      console.error("Failed to download package:", error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold">API Connector Generator</h2>
        <p className="text-gray-600">Auto-generate TypeScript connectors for internal APIs</p>
      </div>

      {/* Available APIs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(availableAPIs).map(([apiKey, apiInfo]) => (
          <Card key={apiKey} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{apiInfo.name}</span>
                <Code className="h-5 w-5 text-blue-600" />
              </CardTitle>
              <CardDescription>{apiInfo.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm text-gray-600">Endpoints: {apiInfo.endpoint_count}</span>
                <Badge variant="outline">TypeScript</Badge>
              </div>
              <div className="flex space-x-2">
                <Button 
                  onClick={() => generateConnector(apiKey)}
                  disabled={loading}
                  className="flex-1"
                >
                  {loading ? (
                    <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Code className="h-4 w-4 mr-2" />
                  )}
                  Generate
                </Button>
                <Button 
                  onClick={() => downloadPackage(apiKey)}
                  variant="outline"
                  size="icon"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Generated Connector Preview */}
      {generatedConnector && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span>Generated Connector: {selectedAPI.replace('_', ' ')}</span>
            </CardTitle>
            <CardDescription>
              Ready-to-use TypeScript connector with documentation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="client" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="client">Client Code</TabsTrigger>
                <TabsTrigger value="config">Configuration</TabsTrigger>
                <TabsTrigger value="docs">Documentation</TabsTrigger>
                <TabsTrigger value="structure">Structure</TabsTrigger>
              </TabsList>
              
              <TabsContent value="client" className="mt-4">
                <div className="relative">
                  <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-96">
                    <code>{generatedConnector.connector_code}</code>
                  </pre>
                  <Button 
                    onClick={() => navigator.clipboard.writeText(generatedConnector.connector_code)}
                    className="absolute top-2 right-2"
                    size="sm"
                    variant="outline"
                  >
                    Copy
                  </Button>
                </div>
              </TabsContent>
              
              <TabsContent value="config" className="mt-4">
                <div className="relative">
                  <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-96">
                    <code>{generatedConnector.config_template}</code>
                  </pre>
                  <Button 
                    onClick={() => navigator.clipboard.writeText(generatedConnector.config_template)}
                    className="absolute top-2 right-2"
                    size="sm"
                    variant="outline"
                  >
                    Copy
                  </Button>
                </div>
              </TabsContent>
              
              <TabsContent value="docs" className="mt-4">
                <div className="prose max-w-none">
                  <div 
                    className="bg-gray-50 p-4 rounded-lg"
                    dangerouslySetInnerHTML={{ 
                      __html: generatedConnector.documentation.replace(/\n/g, '<br>') 
                    }}
                  />
                </div>
              </TabsContent>
              
              <TabsContent value="structure" className="mt-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-sm">
                    <code>{JSON.stringify(generatedConnector.directory_structure, null, 2)}</code>
                  </pre>
                </div>
              </TabsContent>
            </Tabs>
            
            <Separator className="my-4" />
            
            <div className="flex space-x-2">
              <Button onClick={() => downloadPackage(selectedAPI)} className="flex-1">
                <Download className="h-4 w-4 mr-2" />
                Download Complete Package
              </Button>
              <Button 
                onClick={() => generateConnector(selectedAPI)}
                variant="outline"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Regenerate
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Main App Component
const Home = () => {
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await axios.get(`${API}/dashboard`);
        setDashboardData(response.data);
      } catch (error) {
        console.error("Failed to fetch system status:", error);
      }
    };

    fetchSystemStatus();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-4">
              <img 
                src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" 
                alt="Logo" 
                className="h-8 w-8"
              />
              <div>
                <h1 className="text-xl font-semibold">DevOps Automation Platform</h1>
                <p className="text-sm text-gray-600">Cold Start Prediction & API Connector Generator</p>
              </div>
            </div>
            {dashboardData && (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm">
                  <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                  <span>System Online</span>
                </div>
                <Badge variant="outline">
                  {dashboardData.system_status.timestamp.split('T')[1].split('.')[0]}
                </Badge>
              </div>
            )}
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Tabs defaultValue="predictions" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="predictions" className="flex items-center space-x-2">
              <Zap className="h-4 w-4" />
              <span>Cold Start Predictions</span>
            </TabsTrigger>
            <TabsTrigger value="connectors" className="flex items-center space-x-2">
              <Code className="h-4 w-4" />
              <span>API Connector Generator</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="predictions" className="mt-6">
            <ColdStartDashboard />
          </TabsContent>
          
          <TabsContent value="connectors" className="mt-6">
            <ConnectorGenerator />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;