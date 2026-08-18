// src/components/layout/ChatInput.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './ChatInput.css';

const ChatInput = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    navigate('/ai', { state: { prompt: prompt.trim() } });
    setPrompt('');
  };

  return (
    <div className="chat-input-bar">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Posez une question à l'assistant IA..."
          rows={1}
          className="chat-input-field"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button type="submit" className="chat-input-send" disabled={!prompt.trim()}>
          Envoyer
        </button>
      </form>
    </div>
  );
};

export default ChatInput;
