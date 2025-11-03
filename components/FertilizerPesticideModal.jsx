import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '../api/api';

const FertilizerPesticideModal = ({ open, onClose, onReportGenerated }) => {
  const [cropName, setCropName] = useState('');
  const [soilType, setSoilType] = useState('Sandy');
  const [nitrogen, setNitrogen] = useState('');
  const [phosphorus, setPhosphorus] = useState('');
  const [potassium, setPotassium] = useState('');
  const [moisture, setMoisture] = useState('');
  const [temperature, setTemperature] = useState('');
  const [humidity, setHumidity] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRecommendation = async () => {
    if (!cropName.trim()) {
      setError('Please enter a crop name');
      return;
    }
    if (!soilType.trim()) {
      setError('Please select a soil type');
      return;
    }
    if (!nitrogen || !phosphorus || !potassium || !moisture || !temperature) {
      setError('Please fill all required fields (NPK, Moisture, Temperature)');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.getFertilizerRecommendation({
        crop_name: cropName,
        soil_type: soilType,
        nitrogen: parseFloat(nitrogen),
        phosphorus: parseFloat(phosphorus),
        potassium: parseFloat(potassium),
        moisture: parseFloat(moisture),
        temperature: parseFloat(temperature),
        humidity: humidity ? parseFloat(humidity) : null
      });
      const report = result.report;
      
      // Send report to chat
      if (onReportGenerated) {
        onReportGenerated(report);
      }
      
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to generate recommendation');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto p-4">
        <DialogHeader className="pb-2">
          <DialogTitle className="text-lg font-semibold">Fertilizer Recommendation</DialogTitle>
        </DialogHeader>

        <div className="w-full">
          <div className="space-y-2 mt-2">
            <div className="text-xs text-muted-foreground mb-2">
              Fill details below. Results appear in chat.
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label htmlFor="crop-name" className="text-xs">Crop *</Label>
                <Input
                  id="crop-name"
                  placeholder="Rice, Wheat"
                  value={cropName}
                  onChange={(e) => setCropName(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="soil-type" className="text-xs">Soil *</Label>
                <Select value={soilType} onValueChange={setSoilType} disabled={isLoading}>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Sandy">Sandy</SelectItem>
                    <SelectItem value="Clayey">Clayey</SelectItem>
                    <SelectItem value="Loamy">Loamy</SelectItem>
                    <SelectItem value="Silty">Silty</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">NPK *</Label>
              <div className="grid grid-cols-3 gap-1.5">
                <Input
                  id="nitrogen"
                  type="number"
                  placeholder="N"
                  value={nitrogen}
                  onChange={(e) => setNitrogen(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
                <Input
                  id="phosphorus"
                  type="number"
                  placeholder="P"
                  value={phosphorus}
                  onChange={(e) => setPhosphorus(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
                <Input
                  id="potassium"
                  type="number"
                  placeholder="K"
                  value={potassium}
                  onChange={(e) => setPotassium(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              <div className="space-y-1">
                <Label htmlFor="moisture" className="text-xs">Moisture % *</Label>
                <Input
                  id="moisture"
                  type="number"
                  placeholder="50"
                  value={moisture}
                  onChange={(e) => setMoisture(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="temperature" className="text-xs">Temp °C *</Label>
                <Input
                  id="temperature"
                  type="number"
                  placeholder="28"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="humidity" className="text-xs">Humidity %</Label>
                <Input
                  id="humidity"
                  type="number"
                  placeholder="65"
                  value={humidity}
                  onChange={(e) => setHumidity(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>
            </div>

            {error && (
              <div className="text-red-600 text-xs bg-red-50 p-1.5 rounded">{error}</div>
            )}

            <Button
              onClick={handleRecommendation}
              disabled={isLoading || !cropName.trim() || !nitrogen || !phosphorus || !potassium || !moisture || !temperature}
              className="w-full mt-2 h-9 font-medium text-sm"
            >
              {isLoading ? 'Generating...' : 'Get Recommendation →'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default FertilizerPesticideModal;

