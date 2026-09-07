// src/pages/AI.jsx
// Interface conversationnelle style DeepSeek
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { aiService } from '../services/api';
import { useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext';
import './AIConversation.css';

// ======================================================
// CONSTANTES
// ======================================================

const SUGGESTIONS = [
  { icon: 'ti-package', text: 'Quel est l\'état du stock ?' },
  { icon: 'ti-chart-line', text: 'Quel est notre chiffre d\'affaires ?' },
  { icon: 'ti-sparkles', text: 'Quelles sont les prévisions de ventes ?' },
  { icon: 'ti-trophy', text: 'Quels sont les produits les plus vendus ?' },
  { icon: 'ti-credit-card', text: 'Quel est le montant des factures impayées ?' },
  { icon: 'ti-users', text: 'Combien de clients avons-nous ?' },
];

const FOLLOW_UP_PROMPTS = [
  { icon: 'ti-package', text: 'État du stock' },
  { icon: 'ti-chart-line', text: 'Chiffre d\'affaires' },
  { icon: 'ti-sparkles', text: 'Prévisions de ventes' },
  { icon: 'ti-trophy', text: 'Top produits' },
  { icon: 'ti-credit-card', text: 'Factures impayées' },
  { icon: 'ti-users', text: 'Nombre de clients' },
];

// ======================================================
// UTILITAIRES
// ======================================================

const formatTime = (date) => {
  return date.toLocaleTimeString('mg-MG', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Extrait le bloc "Sources" de la réponse de l'assistant.
 * Le backend ajoute : "\n\n**Sources** :\n- title: url"
 */
const extractSources = (text) => {
  if (!text) return { content: '', sources: [] };

  const marker = '**Sources**';
  const index = text.indexOf(marker);

  if (index === -1) {
    return { content: text, sources: [] };
  }

  const content = text.substring(0, index).trimEnd();
  const sourcesPart = text.substring(index + marker.length).trim();

  const sources = [];
  const lines = sourcesPart.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();
    // Format interne : "- provider : réponse générée"
    const internalMatch = trimmed.match(/^-\s*([^:]+):\s*réponse générée/i);
    if (internalMatch) {
      sources.push({
        name: internalMatch[1].trim(),
        url: '',
        snippet: 'Réponse générée par cette source',
      });
      continue;
    }

    // Format web : "- title: url"
    const webMatch = trimmed.match(/^-\s*(.+?):\s*(https?:\/\/\S+)/i);
    if (webMatch) {
      sources.push({
        name: webMatch[1].trim(),
        url: webMatch[2].trim(),
        snippet: '',
      });
      continue;
    }

    // Format simple : "- texte"
    if (trimmed.startsWith('- ') && trimmed.length > 2) {
      sources.push({
        name: trimmed.substring(2).trim(),
        url: '',
        snippet: '',
      });
    }
  }

  return { content, sources };
};

// Parse simple du markdown renvoyé par l'assistant
const renderMarkdown = (text) => {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];
  let listItems = [];
  let listKey = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul className="ai-msg-list" key={`list-${listKey++}`}>
          {listItems.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Ligne vide -> flush liste
    if (!trimmed) {
      flushList();
      return;
    }

    // Élément de liste
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.substring(2);
      // Rendu du gras **texte**
      const parts = content.split(/\*\*(.+?)\*\*/g);
      listItems.push(
        <span key={`li-${index}`}>
          {parts.map((part, i) =>
            i % 2 === 1 ? <strong key={i}>{part}</strong> : part
          )}
        </span>
      );
      return;
    }

    // Ligne normale
    flushList();
    const parts = line.split(/\*\*(.+?)\*\*/g);
    elements.push(
      <p className="ai-msg-paragraph" key={`p-${index}`}>
        {parts.map((part, i) =>
          i % 2 === 1 ? <strong key={i}>{part}</strong> : part
        )}
      </p>
    );
  });

  flushList();
  return elements;
};

// ======================================================
// COMPOSANT PRINCIPAL
// ======================================================

const AI = () => {
  const location = useLocation();
  const { user } = useAuth();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasConversation, setHasConversation] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const pendingPromptRef = useRef(null);

  const userName = user?.prenom || 'Utilisateur';

  // ======================================================
  // CONSTRUCTION DU CONTEXTE POUR LE BACKEND
  // ======================================================

  // Convertit les messages en format conversation backend :
  // [{ role: 'user'|'assistant', content: '...' }]
  const buildConversationContext = (currentMessages) => {
    return currentMessages
      .filter((m) => !m.isError && (m.role === 'user' || m.role === 'assistant'))
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));
  };

  // ======================================================
  // AUTO-SCROLL
  // ======================================================

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // ======================================================
  // PROMPT DEPUIS ChatInput (navigation)
  // ======================================================

  useEffect(() => {
    if (location.state?.prompt) {
      pendingPromptRef.current = location.state.prompt;
      // Nettoyer le state pour éviter les re-déclenchements
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // ======================================================
  // ENVOI DE MESSAGE (profite du contexte multi-tours)
  // ======================================================

  const sendMessage = useCallback(async (text) => {
    const prompt = (text ?? input).trim();
    if (!prompt || isLoading) return;

    // Ajouter le message utilisateur
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: prompt,
      time: formatTime(new Date()),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setHasConversation(true);

    try {
      // Construire le contexte de conversation à partir des messages
      // (inclut le nouveau message utilisateur)
      const currentMessages = [...messages, userMessage];
      const conversation = buildConversationContext(currentMessages);

      const response = await aiService.askAssistant({
        prompt,
        conversation,
      });

      const rawResponse = response.data?.response || 'Désolé, je n\'ai pas pu traiter votre demande.';

      // Extraire les sources éventuelles de la réponse
      const { content: assistantContent, sources } = extractSources(rawResponse);

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: assistantContent,
        sources: sources.length > 0 ? sources : undefined,
        time: formatTime(new Date()),
      };

      // Petit délai pour laisser voir l'indicateur de frappe
      setTimeout(() => {
        setMessages((prev) => [...prev, assistantMessage]);
        setIsLoading(false);
      }, 400);
    } catch (err) {
      console.error('Erreur assistant IA:', err);
      const msg = err.response?.data?.message || err.response?.data?.error || 'Échec de la connexion à l\'assistant IA';

      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Attention : ${msg}`,
        time: formatTime(new Date()),
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
      toast.error(msg);
    }
  }, [input, isLoading, messages]);

  // ======================================================
  // GESTION DU FORMULAIRE
  // ======================================================

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (text) => {
    sendMessage(text);
  };

  // ======================================================
  // EFFACER LA CONVERSATION
  // ======================================================

  const clearConversation = () => {
    setMessages([]);
    setHasConversation(false);
    setInput('');
    inputRef.current?.focus();
  };

  // ======================================================
  // COPIER LA RÉPONSE
  // ======================================================

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Réponse copiée !');
    } catch {
      toast.error('Impossible de copier');
    }
  };

  // ======================================================
  // RENDU
  // ======================================================

  return (
    <div className="ai-page">
      {!hasConversation ? (
        // ==================== ÉCRAN D'ACCUEIL ====================
        <div className="ai-welcome">
          <div className="ai-welcome-icon"><i className="ti ti-sparkles" aria-hidden="true" /></div>
          <h1>Assistant IA ERP</h1>
          <p>
            Posez une question sur vos stocks, ventes, clients, factures
            ou prévisions. L'assistant analyse vos données et garde le
            contexte de votre conversation.
          </p>

          <div className="ai-suggestion-grid">
            {SUGGESTIONS.map((suggestion, index) => (
              <button
                key={index}
                className="ai-suggestion-card"
                onClick={() => handleSuggestionClick(suggestion.text)}
              >
                <span className="ai-suggestion-emoji"><i className={`ti ${suggestion.icon}`} aria-hidden="true" /></span>
                <span className="ai-suggestion-text">{suggestion.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        // ==================== CONVERSATION ====================
        <div className="ai-chat-container">
          <div className="ai-chat-toolbar">
            <div className="ai-chat-title">
              <span className="ai-chat-title-dot" />
              Assistant IA
            </div>
            <button className="ai-clear-btn" onClick={clearConversation}>
              <i className="ti ti-trash" aria-hidden="true" /> Nouvelle conversation
            </button>
          </div>

          <div className="ai-messages">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`ai-msg ${msg.role}${msg.isError ? ' error' : ''}`}
              >
                <div className="ai-msg-avatar">
                  {msg.role === 'assistant' ? <i className="ti ti-sparkles" aria-hidden="true" /> : (userName[0] || 'U').toUpperCase()}
                </div>
                <div className="ai-msg-body">
                  <div className="ai-msg-meta">
                    <span className="ai-msg-name">
                      {msg.role === 'assistant' ? 'Assistant IA' : userName}
                    </span>
                    <span className="ai-msg-time">{msg.time}</span>
                  </div>
                  <div className="ai-msg-content">
                    {msg.role === 'assistant'
                      ? renderMarkdown(msg.content)
                      : msg.content}
                  </div>

                  {/* Sources (IA externe / recherche web) */}
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <div className="ai-sources">
                      <div className="ai-sources-title"><i className="ti ti-link" aria-hidden="true" /> Sources</div>
                      <ul className="ai-sources-list">
                        {msg.sources.map((source, i) => (
                          <li key={i} className="ai-source-item">
                            {source.url ? (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {source.name}
                              </a>
                            ) : (
                              <span>{source.name}</span>
                            )}
                            {source.snippet && ` — ${source.snippet}`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.role === 'assistant' && !msg.isError && (
                      <button
                        className="ai-copy-btn"
                        onClick={() => copyToClipboard(msg.content)}
                      >
                        <i className="ti ti-clipboard" aria-hidden="true" /> Copier
                      </button>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="ai-msg assistant">
                <div className="ai-msg-avatar"><i className="ti ti-sparkles" aria-hidden="true" /></div>
                <div className="ai-msg-body">
                  <div className="ai-msg-meta">
                    <span className="ai-msg-name">Assistant IA</span>
                  </div>
                  <div className="ai-msg-content">
                    <div className="ai-typing">
                      <span className="ai-typing-dot" />
                      <span className="ai-typing-dot" />
                      <span className="ai-typing-dot" />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Suggestions rapides après la dernière réponse */}
            {!isLoading && messages.length > 0 && (
              <div className="ai-quick-prompts">
                {FOLLOW_UP_PROMPTS.map((prompt, index) => (
                  <button
                    key={index}
                    className="ai-quick-prompt"
                    onClick={() => handleSuggestionClick(prompt.text)}
                  >
                    <i className={`ti ${prompt.icon}`} aria-hidden="true" /> {prompt.text}
                  </button>
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/* ==================== BARRE DE SAISIE ==================== */}
      <div className="ai-input-wrapper">
        <form onSubmit={handleSubmit} className="ai-input-container">
          <textarea
            ref={inputRef}
            className="ai-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Posez une question à l'assistant IA..."
            rows={1}
            autoFocus
          />
          <button
            type="submit"
            className={`ai-send-btn${isLoading ? ' thinking' : ''}`}
            disabled={!input.trim() || isLoading}
            aria-label="Envoyer"
          >
            {isLoading ? <i className="ti ti-loader-2" aria-hidden="true" /> : <i className="ti ti-send" aria-hidden="true" />}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AI;