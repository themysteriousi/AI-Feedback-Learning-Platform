/**
 * API client for the AI Feedback Learning Platform
 */

// Dynamically set API Gateway URL from local storage or environment
let API_BASE_URL = localStorage.getItem('FEEDBACK_API_URL') || import.meta.env.VITE_API_URL || '';

export const getApiUrl = () => API_BASE_URL;

export const setApiUrl = (url) => {
  API_BASE_URL = url.trim().replace(/\/$/, ''); // strip trailing slash
  localStorage.setItem('FEEDBACK_API_URL', API_BASE_URL);
  return API_BASE_URL;
};

/**
 * Generate a response from the Bedrock backend
 * @param {string} prompt - User prompt
 * @returns {Promise<{response: string, model_id: string, is_mock: boolean}>}
 */
export async function generateResponse(prompt) {
  if (!API_BASE_URL) {
    console.warn("API URL not set. Falling back to local mock simulation.");
    return mockGenerateResponse(prompt);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    return {
      response: data.response,
      model_id: data.model_id || 'anthropic.claude-3-haiku-20240307-v1:0',
      is_mock: false
    };
  } catch (error) {
    console.error("API Error during /generate:", error);
    // Return error mock response so the UI doesn't crash but informs the user
    throw error;
  }
}

/**
 * Send telemetry and explicit feedback to the feedback Lambda
 * @param {object} telemetryPayload - Raw telemetry data from tracker
 * @param {object} feedbackData - Explicit feedback answers
 * @returns {Promise<{success: boolean, session_id: string}>}
 */
export async function submitFeedback(telemetryTracker, feedbackData) {
  // Get payload from telemetry tracker
  const rawPayload = telemetryTracker.getFeedbackPayload(feedbackData);
  if (!rawPayload) return { success: false, error: 'No active interaction' };

  // Map client keys to exact DynamoDB/Lambda expectations
  const backendPayload = {
    session_id: rawPayload.session_id,
    prompt: rawPayload.prompt,
    response: rawPayload.response,
    model_id: rawPayload.model_id,
    
    // Explicit
    star_rating: rawPayload.rating,
    thumbs: rawPayload.thumb,
    user_comment: rawPayload.comment,
    accuracy_rating: rawPayload.accuracy_rating,
    relevance_rating: rawPayload.relevance_rating,
    
    // Implicit
    session_duration_secs: Math.max(1, Math.round(rawPayload.metadata.read_duration_ms / 1000)),
    reread_count: rawPayload.metadata.scroll_events_count,
    followup_question_count: 0, // could be incremented in App state
    query_reformulation_count: 0,
    conversation_abandoned: rawPayload.metadata.is_abandoned
  };

  if (!API_BASE_URL) {
    console.log("[MOCK FEEDBACK SUBMITTED]", backendPayload);
    // Simulate successful API call
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true, session_id: backendPayload.session_id, is_mock: true });
      }, 500);
    });
  }

  try {
    const response = await fetch(`${API_BASE_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendPayload),
    });

    if (!response.ok) {
      throw new Error(`Feedback server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      session_id: data.session_id,
      is_mock: false
    };
  } catch (error) {
    console.error("API Error during /feedback:", error);
    throw error;
  }
}

/**
 * Premium Mock Response Generator for demonstration
 */
function mockGenerateResponse(prompt) {
  return new Promise((resolve) => {
    setTimeout(() => {
      let responseText = "";
      const lower = prompt.toLowerCase();

      if (lower.includes("hello") || lower.includes("hi")) {
        responseText = "Hello! I am Llama 3 (running in local simulation mode). How can I assist you today on the AI Feedback Learning Platform?";
      } else if (lower.includes("dpo") || lower.includes("preference") || lower.includes("fine-tuning")) {
        responseText = "Direct Preference Optimization (DPO) is a method that fine-tunes LLMs to align with human preferences directly, without needing a separate reward model. In this project, we extract thumbs up/down feedback pairs from S3, format them as chosen/rejected prompts, and run DPO fine-tuning using a free Google Colab GPU.";
      } else if (lower.includes("pii") || lower.includes("presidio") || lower.includes("redact")) {
        responseText = "PII redaction is handled by Microsoft Presidio. When feedback is written to DynamoDB, its stream triggers a Lambda layer containing Presidio, which runs regex and NLP to redact names, emails, addresses, and credit cards before transferring the logs to the S3 data lake.";
      } else if (lower.includes("cost") || lower.includes("budget") || lower.includes("price")) {
        responseText = "This platform is optimized for near-zero running cost. It utilizes AWS Lambda, DynamoDB (PAY_PER_REQUEST), API Gateway, and S3 Glacier lifecycle rules. It stays within the AWS Free Tier for low-volume testing, and includes a $2.00 monthly CloudWatch budget alarm to prevent unexpected costs.";
      } else {
        responseText = `Received prompt: "${prompt}".\n\nThis is a mock response from the frontend fallback system. Once you deploy the Terraform infrastructure under the \`infrastructure/\` directory, you can paste the output \`api_url\` into the settings gear above to enable live inference from Amazon Bedrock and trigger the automated feedback collection pipeline.`;
      }

      resolve({
        response: responseText,
        model_id: 'meta.llama3-8b-instruct-v1:0 (Local Sim)',
        is_mock: true
      });
    }, 1000);
  });
}
