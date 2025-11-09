import api from './api';

export const chatWithAI = (payload) => api.post('/api/v1/ai/chat/', payload);

export const sendAIFeedback = ({ conversationId, rating, notes }) =>
  api.post('/api/v1/ai/feedback/', {
    conversation_id: conversationId,
    rating,
    notes,
  });

export const fetchAISuggestions = () => api.get('/api/v1/ai/suggestions/');

export const updateAISuggestion = ({ suggestionId, status }) =>
  api.post('/api/v1/ai/suggestions/', {
    suggestion_id: suggestionId,
    status,
  });

export const trainAI = ({ key, value, scope = 'user' }) =>
  api.post('/api/v1/ai/train/', { key, value, scope });

export const fetchAIConversationHistory = ({ conversationId, limit } = {}) =>
  api.get('/api/v1/ai/conversations/history/', {
    params: {
      conversation_id: conversationId,
      limit,
    },
  });

export const fetchAITrainingExamples = (params = {}) =>
  api.get('/api/v1/ai/training-examples/', {
    params,
  });

export const updateAITrainingExample = ({ id, status, metadata, notes }) =>
  api.patch(`/api/v1/ai/training-examples/${id}/`, { status, metadata, notes });

export const fetchLoRARuns = (params = {}) =>
  api.get('/api/v1/ai/ops/lora-runs/', { params });

export const triggerLoRARun = ({ adapterType = 'lora', datasetLimit } = {}) =>
  api.post('/api/v1/ai/ops/lora-runs/', {
    adapter_type: adapterType,
    dataset_limit: datasetLimit,
  });

export const bulkUpdateAITrainingExamples = ({ ids, status, notes, metadata }) =>
  api.post('/api/v1/ai/training-examples/bulk/', {
    ids,
    status,
    notes,
    metadata,
  });

export const fetchAIPreferences = (params = {}) =>
  api.get('/api/v1/ai/preferences/', { params });

export const saveAIPreference = ({ id, key, value, scope = 'company' }) => {
  const payload = {
    key,
    value,
    scope,
  };
  if (id) {
    return api.patch(`/api/v1/ai/preferences/${id}/`, payload);
  }
  return api.post('/api/v1/ai/preferences/', payload);
};

export const deleteAIPreference = (id) => api.delete(`/api/v1/ai/preferences/${id}/`);

export const executeAIAction = ({ action, payload }) =>
  api.post('/api/v1/ai/actions/', { action, payload });

export const trackMetadataInterest = ({ kind, entity, ...rest }) =>
  api.post('/api/v1/ai/metadata/interest/', { kind, entity, ...rest });

export const fetchAIAgenda = () => api.get('/api/v1/ai/agenda/');
