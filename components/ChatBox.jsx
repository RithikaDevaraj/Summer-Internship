import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Send, User, Bot, Leaf, AlertCircle, CheckCircle } from 'lucide-react';
import { apiClient } from '../api/api';
import Loader from './Loader';

// Minimal markdown renderer (bold, lists, line breaks) without extra deps
const renderMarkdown = (text) => {
  if (!text) return null;
  // Escape HTML
  const esc = (s) => s
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
  // Normalize newlines
  const norm = String(text).replace(/\r\n?/g, '\n');
  const paragraphs = norm.split(/\n\n+/);
  const boldify = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  const toList = (lines, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const items = lines.map(l => l.replace(/^\s*(?:[-*]|\d+\.)\s+/, ''))
      .map(l => `<li>${boldify(l)}</li>`)
      .join('');
    return `<${tag} class="ml-5 list-${ordered ? 'decimal' : 'disc'}">${items}</${tag}>`;
  };
  const html = paragraphs.map(p => {
    const lines = p.split('\n');
    const isUl = lines.every(l => /^\s*[-*]\s+/.test(l));
    const isOl = !isUl && lines.every(l => /^\s*\d+\.\s+/.test(l));
    if (isUl) return toList(lines, false);
    if (isOl) return toList(lines, true);
    return `<p>${boldify(p).replace(/\n/g, '<br/>')}</p>`;
  }).join('');
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
};

const ChatBox = ({ onReportReceived, reportContent }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'नमस्ते! I am Prakriti, your AI agricultural advisor. Ask me about crops, pests, diseases, or farming practices in India.',
      timestamp: new Date(),
      sources: { knowledge_graph: [], documents: [] }
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Handle external reports
  useEffect(() => {
    if (reportContent) {
      const reportMessage = {
        id: Date.now(),
        type: 'bot',
        content: reportContent,
        timestamp: new Date(),
        sources: { knowledge_graph: [], documents: [] }
      };
      setMessages(prev => [...prev, reportMessage]);
      if (onReportReceived) {
        onReportReceived();
      }
    }
  }, [reportContent, onReportReceived]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.processQuery(inputValue);
      
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.response,
        timestamp: new Date(response.timestamp),
        sources: response.sources,
        metadata: {
          kg_results: response.kg_results,
          vector_results: response.vector_results,
          context_used: response.context_used,
        }
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to get response. Please try again.');
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: 'I apologize, but I encountered an error processing your query. Please check if the backend server is running and try again.',
        timestamp: new Date(),
        isError: true,
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const MessageBubble = ({ message }) => {
    const isUser = message.type === 'user';
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2 max-w-[80%]`}>
          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-blue-500 ml-2' : 'bg-green-500 mr-2'
          }`}>
            {isUser ? <User className="w-4 h-4 text-white" /> : <Leaf className="w-4 h-4 text-white" />}
          </div>
          
          <div className={`rounded-lg px-4 py-2 ${
            isUser 
              ? 'bg-blue-500 text-white' 
              : message.isError 
                ? 'bg-red-50 text-red-800 border border-red-200' 
                : 'bg-gray-100 text-gray-800'
          }`}>
            {message.type === 'bot' ? (
              <div className="prose prose-sm max-w-none">{renderMarkdown(message.content)}</div>
            ) : (
              <p className="whitespace-pre-wrap">{message.content}</p>
            )}
            
            {/* Show sources for bot messages */}
            {!isUser && message.sources && (
              <div className="mt-2 pt-2 border-t border-gray-200">
                {message.sources.knowledge_graph.length > 0 && (
                  <div className="mb-1">
                    <span className="text-xs font-semibold text-gray-600">Knowledge Graph: </span>
                    {message.sources.knowledge_graph.map((source, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs mr-1">
                        {source}
                      </Badge>
                    ))}
                  </div>
                )}
                
                {message.sources.documents.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-gray-600">Documents: </span>
                    {message.sources.documents.map((source, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs mr-1">
                        {source}
                      </Badge>
                    ))}
                  </div>
                )}
                
                {message.metadata && (
                  <div className="mt-1 text-xs text-gray-500">
                    KG: {message.metadata.kg_results} | Docs: {message.metadata.vector_results}
                    {message.metadata.context_used && (
                      <CheckCircle className="inline w-3 h-3 ml-1 text-green-500" />
                    )}
                  </div>
                )}
              </div>
            )}
            
            <div className="text-xs opacity-70 mt-1">
              {formatTimestamp(message.timestamp)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const suggestedQuestions = [
    "What pests affect rice in Tamil Nadu?",
    "How to control cotton bollworm?",
    "Best crops for monsoon season",
    "Wheat diseases in Punjab",
    "Organic farming methods for vegetables"
  ];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center space-x-2">
          <Leaf className="w-5 h-5 text-green-600" />
          <span>Agricultural Chat Assistant</span>
        </CardTitle>
        {error && (
          <div className="flex items-center space-x-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col p-0">
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="flex items-start space-x-2 max-w-[80%]">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-lg px-4 py-2">
                    <Loader size="sm" text="Thinking..." />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        {/* Suggested questions */}
        {messages.length === 1 && (
          <div className="px-4 py-2 border-t">
            <p className="text-sm text-gray-600 mb-2">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((question, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setInputValue(question)}
                >
                  {question}
                </Button>
              ))}
            </div>
          </div>
        )}
        
        <Separator />
        
        {/* Input area */}
        <div className="p-4">
          <div className="flex space-x-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about crops, pests, diseases, or farming practices..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              size="icon"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};


// Export with forwardRef or prop handling for external reports
export default ChatBox;