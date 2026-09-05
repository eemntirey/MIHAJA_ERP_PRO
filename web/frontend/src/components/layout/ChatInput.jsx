// src/components/layout/ChatInput.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ChatInput.css';

const MAX_HEIGHT = 120;

const ChatInput = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef(null);

  const autoResize = (el) => {
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.min(el.scrollHeight, MAX_HEIGHT);
    el.style.height = `${newHeight}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
  };

  useEffect(() => {
    autoResize(textareaRef.current);
  }, [prompt]);

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
          ref={textareaRef}
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
