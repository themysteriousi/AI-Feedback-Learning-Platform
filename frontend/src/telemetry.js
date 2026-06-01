/**
 * Telemetry Tracker for AI Feedback Platform
 * Tracks implicit telemetry (scrolls, reading duration, focus events, abandonment)
 * and combines it with explicit feedback (star ratings, thumbs up/down, comments)
 */

export class TelemetryTracker {
  constructor() {
    this.sessionId = this._generateUUID();
    this.sessionStartTime = new Date().toISOString();
    this.currentInteraction = null;
    this.interactions = [];
  }

  // Generate simple UUID
  _generateUUID() {
    return 'session-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
  }

  // Start tracking a new interaction (called when prompt is submitted)
  startInteraction(promptText) {
    // If there was a previous interaction that wasn't rated, it's marked as abandoned
    if (this.currentInteraction && !this.currentInteraction.rated) {
      this.currentInteraction.isAbandoned = true;
      this.saveCurrentInteraction();
    }

    this.currentInteraction = {
      interactionId: 'int-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now(),
      prompt: promptText,
      response: '',
      modelId: '',
      timestamp: new Date().toISOString(),
      requestStartTime: performance.now(),
      responseEndTime: null,
      generationLatencyMs: 0,
      readDurationMs: 0,
      scrollEventsCount: 0,
      rated: false,
      isAbandoned: false,
      windowBlursCount: 0,
      hoverDurationMs: 0,
      hoverStartTime: null,
      feedback: null
    };

    // Set up window focus/blur tracking for engagement quality
    this._setupWindowListeners();
  }

  // Record when the response is returned
  recordResponse(responseText, modelId) {
    if (!this.currentInteraction) return;

    this.currentInteraction.response = responseText;
    this.currentInteraction.modelId = modelId;
    this.currentInteraction.responseEndTime = performance.now();
    this.currentInteraction.generationLatencyMs = Math.round(
      this.currentInteraction.responseEndTime - this.currentInteraction.requestStartTime
    );
    this.currentInteraction.readStartTime = performance.now();
  }

  // Increment scroll events for the current response (reread proxy)
  incrementScroll() {
    if (!this.currentInteraction) return;
    this.currentInteraction.scrollEventsCount += 1;
  }

  // Track hover engagement
  startHover() {
    if (!this.currentInteraction || !this.currentInteraction.responseEndTime) return;
    this.currentInteraction.hoverStartTime = performance.now();
  }

  endHover() {
    if (!this.currentInteraction || !this.currentInteraction.hoverStartTime) return;
    const duration = performance.now() - this.currentInteraction.hoverStartTime;
    this.currentInteraction.hoverDurationMs += Math.round(duration);
    this.currentInteraction.hoverStartTime = null;
  }

  // Track if window lost focus during reading
  recordWindowBlur() {
    if (!this.currentInteraction || !this.currentInteraction.responseEndTime) return;
    this.currentInteraction.windowBlursCount += 1;
  }

  // Record explicit feedback
  recordExplicitFeedback(feedbackData) {
    if (!this.currentInteraction) return;

    this.currentInteraction.feedback = {
      rating: feedbackData.rating || null, // 1-5
      thumb: feedbackData.thumb || null,   // 'up' or 'down'
      comment: feedbackData.comment || '',
      relevanceScore: feedbackData.relevanceScore || null,
      accuracyScore: feedbackData.accuracyScore || null
    };
    this.currentInteraction.rated = true;
    this.currentInteraction.isAbandoned = false;

    // Calculate read duration up to rating submission
    if (this.currentInteraction.readStartTime) {
      this.currentInteraction.readDurationMs = Math.round(
        performance.now() - this.currentInteraction.readStartTime
      );
    }
  }

  // Save the current interaction to history and clean up listeners
  saveCurrentInteraction() {
    if (!this.currentInteraction) return null;

    // Calculate final read duration if not already done via rating
    if (this.currentInteraction.readStartTime && this.currentInteraction.readDurationMs === 0) {
      this.currentInteraction.readDurationMs = Math.round(
        performance.now() - this.currentInteraction.readStartTime
      );
    }

    const completed = { ...this.currentInteraction };
    this.interactions.push(completed);
    this.currentInteraction = null;
    this._cleanupWindowListeners();

    return completed;
  }

  // Prepare full payload for POST /feedback API Gateway
  getFeedbackPayload(feedbackData = {}) {
    // Record explicit feedback first
    this.recordExplicitFeedback(feedbackData);
    
    // Save to local interaction history
    const interaction = this.saveCurrentInteraction();
    if (!interaction) return null;

    // Return format matches our schema in DB
    return {
      session_id: this.sessionId,
      prompt_id: interaction.interactionId,
      prompt: interaction.prompt,
      response: interaction.response,
      model_id: interaction.modelId,
      rating: interaction.feedback?.rating || 0,
      thumb: interaction.feedback?.thumb || '',
      comment: interaction.feedback?.comment || '',
      accuracy_rating: interaction.feedback?.accuracyScore || 0,
      relevance_rating: interaction.feedback?.relevanceScore || 0,
      // Metadata schema containing both explicit & implicit telemetry
      metadata: {
        session_start_time: this.sessionStartTime,
        generation_latency_ms: interaction.generationLatencyMs,
        read_duration_ms: interaction.readDurationMs,
        scroll_events_count: interaction.scrollEventsCount,
        is_abandoned: interaction.isAbandoned,
        window_blurs_count: interaction.windowBlursCount,
        hover_duration_ms: interaction.hoverDurationMs,
        client_timestamp: new Date().toISOString()
      }
    };
  }

  // Event handlers for focus/blur (implicit engagement monitoring)
  _setupWindowListeners() {
    this.blurHandler = () => this.recordWindowBlur();
    window.addEventListener('blur', this.blurHandler);
  }

  _cleanupWindowListeners() {
    if (this.blurHandler) {
      window.removeEventListener('blur', this.blurHandler);
    }
  }
}
