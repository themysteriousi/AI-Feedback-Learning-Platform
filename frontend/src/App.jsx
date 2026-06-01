import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Star, 
  ThumbsUp, 
  ThumbsDown, 
  Settings, 
  Sparkles, 
  Cpu, 
  Database, 
  CheckCircle, 
  MessageSquare, 
  Clock, 
  Eye, 
  HelpCircle,
  TrendingUp,
  RotateCcw
} from 'lucide-react';
import { TelemetryTracker } from './telemetry';
import { generateResponse, submitFeedback, getApiUrl, setApiUrl } from './api';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrlState] = useState(getApiUrl());
  
  // Real-time developer telemetry values for UI preview
  const [devStats, setDevStats] = useState({
    sessionId: '',
    scrolls: 0,
    latency: 0,
    readDuration: 0,
    hoverTime: 0
  });

  // Trackers and Refs
  const trackerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const hoverTargetRef = useRef(null);

  // Initialize Telemetry Tracker on mount
  useEffect(() => {
    trackerRef.current = new TelemetryTracker();
    setDevStats(prev => ({
      ...prev,
      sessionId: trackerRef.current.sessionId
    }));

    // Add window unload listener to record abandonment if user closes app
    const handleBeforeUnload = () => {
      if (trackerRef.current && trackerRef.current.currentInteraction) {
        trackerRef.current.currentInteraction.isAbandoned = true;
        trackerRef.current.saveCurrentInteraction();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Render an initial system welcome message
    setMessages([
      {
        id: 'welcome',
        type: 'assistant',
        text: "Welcome to the **AI Feedback Learning Platform**! This interface functions as the frontend client for generating and scoring Bedrock responses. Ask a question to begin collecting telemetry.",
        model_id: 'System Agent',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        system: true
      }
    ]);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Update dev stats on a short interval for demonstration purposes
  useEffect(() => {
    const interval = setInterval(() => {
      if (trackerRef.current) {
        const current = trackerRef.current.currentInteraction;
        const readDur = current?.readStartTime 
          ? Math.round((performance.now() - current.readStartTime))
          : 0;

        setDevStats({
          sessionId: trackerRef.current.sessionId,
          scrolls: current?.scrollEventsCount || 0,
          latency: current?.generationLatencyMs || 0,
          readDuration: current?.readDurationMs || readDur,
          hoverTime: current?.hoverDurationMs || 0
        });
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Handle setting API URL
  const handleSaveSettings = (e) => {
    e.preventDefault();
    const savedUrl = setApiUrl(apiUrl);
    setApiUrlState(savedUrl);
    setShowSettings(false);
  };

  // Handle scrolls in the chat container (implicit reread proxy)
  const handleScroll = () => {
    if (trackerRef.current && trackerRef.current.currentInteraction) {
      trackerRef.current.incrementScroll();
    }
  };

  // Handle Hover Telemetry
  const handleMouseEnterResponse = () => {
    if (trackerRef.current) {
      trackerRef.current.startHover();
    }
  };

  const handleMouseLeaveResponse = () => {
    if (trackerRef.current) {
      trackerRef.current.endHover();
    }
  };

  // Handle Form Submission
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputPrompt.trim() || loading) return;

    const userMessageText = inputPrompt.trim();
    setInputPrompt('');
    setLoading(true);

    // Initialize telemetry capture for this query
    trackerRef.current.startInteraction(userMessageText);

    // Append User Message to State
    const timestampStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [
      ...prev,
      {
        id: 'msg-' + Math.random().toString(36).substr(2, 9),
        type: 'user',
        text: userMessageText,
        timestamp: timestampStr
      }
    ]);

    try {
      // Fire generation API call
      const result = await generateResponse(userMessageText);
      
      // Update telemetry response details
      trackerRef.current.recordResponse(result.response, result.model_id);

      // Append AI Message to State
      setMessages(prev => [
        ...prev,
        {
          id: trackerRef.current.currentInteraction.interactionId,
          type: 'assistant',
          text: result.response,
          model_id: result.model_id,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          is_mock: result.is_mock,
          ratingSubmitted: false,
          feedback: {
            rating: 0,
            thumb: '',
            comment: '',
            relevanceScore: 5,
            accuracyScore: 5
          }
        }
      ]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [
        ...prev,
        {
          id: 'error-' + Date.now(),
          type: 'assistant',
          text: `🚨 **Error calling backend API**: ${err.message || 'Internal connection error'}.\n\nPlease ensure your API Gateway base URL is correct and the lambda function has Bedrock execution permission. You can review your URL in the configuration gear in the top right.`,
          model_id: 'System Diagnostics',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          error: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handle submitting explicit feedback
  const handleSubmitFeedbackData = async (messageId, ratingData) => {
    // Find the message in state
    const msgIndex = messages.findIndex(m => m.id === messageId);
    if (msgIndex === -1) return;

    try {
      // Submit feedback via API (will map variables internally)
      await submitFeedback(trackerRef.current, ratingData);

      // Update state to lock the rating UI and show success badge
      setMessages(prev => {
        const updated = [...prev];
        updated[msgIndex] = {
          ...updated[msgIndex],
          ratingSubmitted: true,
          feedback: ratingData
        };
        return updated;
      });
    } catch (err) {
      alert(`Failed to save feedback: ${err.message}`);
    }
  };

  // Live updates to local feedback draft (stars, thumbs, comments) before clicking submit
  const handleUpdateFeedbackDraft = (messageId, fields) => {
    setMessages(prev => {
      return prev.map(msg => {
        if (msg.id === messageId) {
          return {
            ...msg,
            feedback: {
              ...msg.feedback,
              ...fields
            }
          };
        }
        return msg;
      });
    });
  };

  return (
    <div id="root">
      {/* Simulation/Offline Banner if API URL is not set */}
      {!apiUrl && (
        <div className="simulation-banner">
          <span>⚠️ <strong>Demo Sandbox Mode:</strong> Connected to Local LLM Simulation. Deploy Terraform infrastructure to run live Bedrock queries.</span>
          <button onClick={() => setShowSettings(true)}>Configure AWS Endpoint</button>
        </div>
      )}

      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="logo-icon">
            <Sparkles size={20} />
          </div>
          <div className="brand-text">
            <h1>AI Feedback learning</h1>
            <span>Self-Improving MLOps Portal</span>
          </div>
        </div>

        <div className="header-actions">
          <div className={`api-badge ${apiUrl ? 'connected' : 'mock'}`}>
            <Database size={14} />
            {apiUrl ? 'Live S3 Pipeline' : 'Mock Simulator'}
          </div>
          <button 
            className="settings-toggle"
            onClick={() => setShowSettings(!showSettings)}
            title="Configure Backend Settings"
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Main Layout Workspace */}
      <div className="app-container">
        
        {/* Settings Panel Sidebar */}
        {showSettings && (
          <aside className="settings-panel">
            <h2 className="panel-title">
              <Settings size={18} />
              Platform Configuration
            </h2>
            <form onSubmit={handleSaveSettings}>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label htmlFor="apiUrl">AWS API Gateway URL</label>
                <input
                  type="url"
                  id="apiUrl"
                  placeholder="https://xxxxxx.execute-api.us-east-1.amazonaws.com"
                  value={apiUrl}
                  onChange={(e) => setApiUrlState(e.target.value)}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Provide the API Gateway root URL outputted by your Terraform deployment.
                </span>
              </div>
              <button type="submit" className="btn-save" style={{ width: '100%' }}>
                Apply AWS Connection
              </button>
            </form>

            <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <strong>Architecture Components:</strong>
              <ul style={{ paddingLeft: '1.25rem', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <li><code>POST /generate</code> → Amazon Bedrock LLM</li>
                <li><code>POST /feedback</code> → DynamoDB Store</li>
                <li>DynamoDB Streams → Presidio PII scrubbing</li>
                <li>PII scrubbing → Partitioned S3 Data Lake</li>
              </ul>
            </div>
          </aside>
        )}

        {/* Chat Interface Workspace */}
        <section className="chat-section">
          
          {/* Scrollable messages container */}
          <div 
            className="messages-container" 
            ref={messagesContainerRef}
            onScroll={handleScroll}
          >
            {messages.length <= 1 && !loading ? (
              <div className="welcome-screen">
                <div className="welcome-icon">
                  <MessageSquare size={32} />
                </div>
                <h2>AI MLOps Feedback Portal</h2>
                <p>
                  This portal operates as the collection hub. Write messages to prompt the generative AI model, and then grade its quality to populate the S3 DPO preference training loop.
                </p>
                <div className="features-grid">
                  <div className="feature-card">
                    <h3>🧠 Implicit Telemetry</h3>
                    <p>Scans scroll frequency, reading pace, hover actions, and focal switches.</p>
                  </div>
                  <div className="feature-card">
                    <h3>🔒 PII Protection</h3>
                    <p>Microsoft Presidio redacts personal attributes inside DynamoDB Streams.</p>
                  </div>
                  <div className="feature-card">
                    <h3>📉 Budget Limits</h3>
                    <p>Designed on serverless components to prevent unexpected billing charges.</p>
                  </div>
                  <div className="feature-card">
                    <h3>⚙️ Training Loops</h3>
                    <p>DPO-quantized scripts read the S3 pairs directly in Google Colab.</p>
                  </div>
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isUser = msg.type === 'user';
                const isLastAi = !isUser && index === messages.length - 1;

                return (
                  <div 
                    key={msg.id} 
                    className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}
                    ref={isLastAi ? hoverTargetRef : null}
                    onMouseEnter={isLastAi ? handleMouseEnterResponse : null}
                    onMouseLeave={isLastAi ? handleMouseLeaveResponse : null}
                  >
                    <div className="message-header">
                      {!isUser && <Cpu size={12} />}
                      <span>
                        {isUser ? 'You' : `${msg.model_id}`}
                      </span>
                      <span style={{ fontSize: '0.65rem', fontWeight: 'normal' }}>
                        • {msg.timestamp}
                      </span>
                    </div>

                    <div className="message-bubble">
                      {msg.text}
                    </div>

                    {/* Developer real-time telemetry readout (only for AI responses) */}
                    {!isUser && !msg.system && !msg.error && (
                      <div className="telemetry-indicator">
                        <span><Clock size={10} /> Latency: {msg.is_mock ? '1.0s (Simulated)' : `${devStats.latency}ms`}</span>
                        {isLastAi && (
                          <>
                            <span><Eye size={10} /> scrolls: {devStats.scrolls}</span>
                            <span><TrendingUp size={10} /> read time: {Math.round(devStats.readDuration / 1000)}s</span>
                          </>
                        )}
                      </div>
                    )}

                    {/* Feedback Form drawer (only on AI responses) */}
                    {!isUser && !msg.system && !msg.error && (
                      <div className="feedback-box">
                        {msg.ratingSubmitted ? (
                          <div className="feedback-success-banner">
                            <CheckCircle size={14} />
                            <span>Feedback submitted successfully. Redacted logs saved to S3 bucket.</span>
                          </div>
                        ) : (
                          <>
                            {/* Star rating and Thumbs */}
                            <div className="feedback-row-compact">
                              <span className="feedback-question">Rate this response:</span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                {/* 1-5 Stars */}
                                <div className="stars-container">
                                  {[1, 2, 3, 4, 5].map((star) => (
                                    <button
                                      key={star}
                                      className={`star-btn ${msg.feedback?.rating >= star ? 'active' : ''}`}
                                      onClick={() => handleUpdateFeedbackDraft(msg.id, { rating: star })}
                                    >
                                      <Star size={16} fill={msg.feedback?.rating >= star ? 'currentColor' : 'none'} />
                                    </button>
                                  ))}
                                </div>

                                {/* Up / Down */}
                                <div className="thumbs-container">
                                  <button
                                    className={`thumb-btn ${msg.feedback?.thumb === 'up' ? 'active up' : ''}`}
                                    onClick={() => handleUpdateFeedbackDraft(msg.id, { thumb: 'up' })}
                                  >
                                    <ThumbsUp size={12} /> Yes
                                  </button>
                                  <button
                                    className={`thumb-btn ${msg.feedback?.thumb === 'down' ? 'active down' : ''}`}
                                    onClick={() => handleUpdateFeedbackDraft(msg.id, { thumb: 'down' })}
                                  >
                                    <ThumbsDown size={12} /> No
                                  </button>
                                </div>
                              </div>
                            </div>

                            {/* Detailed metrics (visible once user starts rating or expands) */}
                            {(msg.feedback?.rating > 0 || msg.feedback?.thumb !== '') && (
                              <div className="detailed-feedback">
                                <div className="rating-grid">
                                  <div className="rating-row">
                                    <span>Accuracy (1-5)</span>
                                    <div className="stars-container">
                                      {[1, 2, 3, 4, 5].map((star) => (
                                        <button
                                          key={star}
                                          className={`star-btn ${msg.feedback?.accuracyScore >= star ? 'active' : ''}`}
                                          onClick={() => handleUpdateFeedbackDraft(msg.id, { accuracyScore: star })}
                                        >
                                          <Star size={12} fill={msg.feedback?.accuracyScore >= star ? 'currentColor' : 'none'} />
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                  <div className="rating-row">
                                    <span>Relevance (1-5)</span>
                                    <div className="stars-container">
                                      {[1, 2, 3, 4, 5].map((star) => (
                                        <button
                                          key={star}
                                          className={`star-btn ${msg.feedback?.relevanceScore >= star ? 'active' : ''}`}
                                          onClick={() => handleUpdateFeedbackDraft(msg.id, { relevanceScore: star })}
                                        >
                                          <Star size={12} fill={msg.feedback?.relevanceScore >= star ? 'currentColor' : 'none'} />
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                </div>

                                <textarea
                                  className="feedback-textarea"
                                  placeholder="Provide optional details about this model answer..."
                                  value={msg.feedback?.comment}
                                  onChange={(e) => handleUpdateFeedbackDraft(msg.id, { comment: e.target.value })}
                                />

                                <button
                                  className="submit-feedback-btn"
                                  onClick={() => handleSubmitFeedbackData(msg.id, msg.feedback)}
                                >
                                  Submit & Redact Logs
                                </button>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {/* Response loading element */}
            {loading && (
              <div className="message-wrapper assistant">
                <div className="message-header">
                  <Cpu size={12} />
                  <span>Amazon Bedrock runtime</span>
                </div>
                <div className="message-bubble" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <div className="loading-message">
                    <div className="spinner"></div>
                    <span>Invoking LLM...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Entry Box */}
          <form className="input-section" onSubmit={handleSendMessage}>
            <div className="input-container">
              <input
                type="text"
                className="chat-input"
                placeholder="Ask your LLM a question (e.g. 'How does DPO work?' or 'Explain Presidio PII filtration')"
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                disabled={loading}
              />
              <button 
                type="submit" 
                className="send-btn" 
                disabled={!inputPrompt.trim() || loading}
              >
                <Send size={18} />
              </button>
            </div>
          </form>

        </section>

      </div>
    </div>
  );
}

export default App;
