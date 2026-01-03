"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Bot,
  User,
  Moon,
  Sun,
  RotateCcw,
  Trash2,
  MessageSquare,
  Globe,
  Monitor,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Menu,
  ThumbsUp,
  ThumbsDown
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useTheme } from "next-themes";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// Types
interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  id: string;
  routing_decision?: string;
  intent?: string;
  isStreaming?: boolean;
  feedback?: "up" | "down";
}

// ... existing code ...

interface StreamEvent {
  event?: string;
  data?: any;
  node?: string;
  state?: any;
  query?: string;
  error?: string;
}

interface Session {
  session_id: string;
  summary: string;
  last_updated?: string;
}

const API_BASE_URL = "http://localhost:8000";

const examples = {
  "💰 Financial Lessons": "What are the key financial lessons from Rich Dad Poor Dad?",
  "🎸 Guitar Gallery": "What acoustic guitars are featured on https://www.guitargallery.com.sg/ and what are their prices?",
  "🈯 Translate": "Translate the following to Chinese: 'The quick brown fox jumps over the lazy dog'",
  "🤖 Agents": "How do agents work?",
};

export default function Home() {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { theme, setTheme } = useTheme();
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [historyList, setHistoryList] = useState<Session[]>([]);
  const [currentSummary, setCurrentSummary] = useState("");
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize Mounted State
  useEffect(() => {
    setMounted(true);
    fetchSessions(); // Call the async function
  }, []);

  // Helper Functions
  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions`);
      const data = await res.json();
      if (data.success) {
        setHistoryList(data.sessions);
      }
    } catch (e) {
      console.error("Failed to fetch sessions", e);
    }
  };

  const loadSession = async (id: string, updateUrl = true) => {
    if (updateUrl && id !== sessionId) {
      setSessionId(id);
      localStorage.setItem("session_id", id);
      setMessages([]);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/${id}`);
      const data = await res.json();

      if (data.success && data.history) {
        // Convert BE history to UI messages
        const uiMessages: Message[] = data.history.map((msg: any, idx: number) => ({
          id: `hist-${idx}`,
          role: msg.role,
          content: msg.content,
          timestamp: new Date().toLocaleTimeString(), // approximate
          isStreaming: false
        }));
        setMessages(uiMessages);
      }

      if (data.success && data.summary) {
        setCurrentSummary(data.summary);
      } else {
        setCurrentSummary("");
      }
    } catch (e) {
      console.error("Failed to load session", e);
    }
  };

  // Initialize Session
  useEffect(() => {
    const storedSession = localStorage.getItem("session_id");
    if (storedSession) {
      setSessionId(storedSession);
      loadSession(storedSession, false);
    } else {
      const newId = crypto.randomUUID();
      setSessionId(newId);
      localStorage.setItem("session_id", newId);
    }
    fetchSessions();
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle Send
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      role: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString(),
      id: crypto.randomUUID()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    // Initial Assistant Placeholder
    const assistantMsgId = crypto.randomUUID();
    setMessages(prev => [...prev, {
      role: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString(),
      id: assistantMsgId,
      isStreaming: true
    }]);

    try {
      // 1. Submit to Queue
      const queueRes = await fetch(`${API_BASE_URL}/api/queue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMsg.content,
          session_id: sessionId,
          target_language: targetLanguage === "English" ? null : targetLanguage,
          model: "gpt-4o-mini"
        })
      });

      if (!queueRes.ok) throw new Error("Failed to queue job");

      const { request_id } = await queueRes.json();

      // 2. Listen to SSE
      const evtSource = new EventSource(`${API_BASE_URL}/api/stream/${request_id}`);

      let fullContent = "";
      let metadata = {};

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.event === "connected") return;

          if (data.event === "error") {
            console.error("Stream error:", data.error);
            evtSource.close();
            setIsLoading(false);
            return;
          }

          if (data.event === "complete") {
            evtSource.close();
            setMessages(prev => prev.map(m =>
              m.id === assistantMsgId ? { ...m, isStreaming: false } : m
            ));
            setIsLoading(false);
            return;
          }

          // Handle Node updates (Thinking process)
          if (data.node) {
            // Optional: You could show "Thinking..." steps here
          }

          // Update summary if available
          if (data.state?.summary) {
            setCurrentSummary(data.state.summary);
          }

          // Handle Content
          if (data.state?.final_answer) {
            fullContent = data.state.final_answer;
            metadata = {
              routing: data.state.routing_decision,
              intent: data.state.intent
            };

            setMessages(prev => prev.map(m =>
              m.id === assistantMsgId ? {
                ...m,
                content: fullContent,
                routing_decision: data.state.routing_decision,
                intent: data.state.intent
              } : m
            ));
          }

        } catch (e) {
          console.error("Parse error", e);
        }
      };

      evtSource.onerror = (err) => {
        console.error("EventSource failed:", err);
        evtSource.close();
        setIsLoading(false);
      };

    } catch (e) {
      console.error(e);
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId ? { ...m, content: "❌ Error: Could not reach server.", isStreaming: false } : m
      ));
      setIsLoading(false);
    }
  };

  const handleFeedback = async (msg: Message, type: "up" | "down", idx: number) => {
    // Optimistic UI update
    setMessages(prev => prev.map(m =>
      m.id === msg.id ? { ...m, feedback: type } : m
    ));

    const userQuery = idx > 0 ? messages[idx - 1].content : "";

    try {
      await fetch(`${API_BASE_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message_index: idx,
          feedback_type: type,
          user_query: userQuery,
          assistant_response: msg.content,
          routing_decision: msg.routing_decision,
          intent: msg.intent,
          model_used: "gpt-4o-mini"
        })
      });
    } catch (e) {
      console.error("Feedback failed", e);
    }
  };

  const clearChat = () => {
    setMessages([]);
    const newId = crypto.randomUUID();
    setSessionId(newId);
    localStorage.setItem("session_id", newId);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">

      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 300, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="border-r border-border bg-muted/30 flex flex-col h-full"
          >
            <div className="p-4 border-b border-border">
              <h2 className="font-bold text-lg flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary" />
                Bot Settings
              </h2>
            </div>

            <div className="p-4 space-y-6 flex-1 overflow-auto">
              {/* Language Selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Output Language</label>
                <select
                  className="w-full p-2 rounded-md border border-input bg-background"
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                >
                  {["English", "Chinese", "Spanish", "French", "German", "Japanese"].map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>

              {/* Theme Toggle */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Theme</label>
                <div className="flex gap-2">
                  {mounted ? (
                    <>
                      <button
                        onClick={() => setTheme("light")}
                        className={cn(
                          "flex-1 p-2 rounded-md border flex items-center justify-center gap-2 text-sm",
                          theme === "light" ? "bg-primary text-primary-foreground border-primary" : "bg-card hover:bg-accent"
                        )}
                      >
                        <Sun className="w-4 h-4" /> Light
                      </button>
                      <button
                        onClick={() => setTheme("dark")}
                        className={cn(
                          "flex-1 p-2 rounded-md border flex items-center justify-center gap-2 text-sm",
                          theme === "dark" ? "bg-primary text-primary-foreground border-primary" : "bg-card hover:bg-accent"
                        )}
                      >
                        <Moon className="w-4 h-4" /> Dark
                      </button>
                    </>
                  ) : (
                    // Skeleton or default state during SSR
                    <div className="flex-1 p-2 rounded-md border flex items-center justify-center gap-2 text-sm bg-muted opacity-50">
                      Loading...
                    </div>
                  )}
                </div>
              </div>

              {/* History List */}
              <div className="flex-1 overflow-auto">
                <h3 className="text-sm font-medium mb-2 text-muted-foreground uppercase tracking-wider sticky top-0 bg-muted/30 pt-2 pb-1">History</h3>
                {historyList.length === 0 ? (
                  <div className="text-sm text-muted-foreground italic">No previous sessions found.</div>
                ) : (
                  <div className="space-y-1">
                    {historyList.map((session) => (
                      <div key={session.session_id} className="flex items-center gap-1 group/item">
                        <button
                          onClick={() => loadSession(session.session_id)}
                          className={cn(
                            "flex-1 text-left p-2 rounded-md text-sm hover:bg-accent transition-colors block overflow-hidden",
                            sessionId === session.session_id && "bg-accent font-medium text-primary"
                          )}
                        >
                          <div className="truncate font-medium">{session.summary || `Session ${session.session_id.substring(5)}`}</div>
                          {session.last_updated ? (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              {new Date(session.last_updated).toLocaleString()}
                            </div>
                          ) : (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              No timestamp
                            </div>
                          )}
                        </button>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            setSessionToDelete(session.session_id);
                          }}
                          className="p-2 text-muted-foreground hover:text-destructive opacity-0 group-hover/item:opacity-100 transition-opacity"
                          title="Delete Chat"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-border space-y-3">
              <div className="bg-background/50 p-3 rounded-md border border-border/50">
                <h4 className="text-xs font-semibold mb-1 flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" /> Summary
                </h4>
                <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                  {currentSummary || "Summary will appear here after the conversation grows longer."}
                </p>
              </div>
              <div className="text-xs text-muted-foreground">Session: {sessionId.slice(0, 8)}...</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full relative">

        {/* Header */}
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-accent rounded-md"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="font-bold text-xl flex items-center gap-2">
              <img src="/bot-icon.png" className="w-8 h-8 rounded-full" alt="Bot" />
              Knowledge Bot
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={clearChat}
              className="text-sm flex items-center gap-2 px-3 py-2 text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              New Chat
            </button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-80 space-y-8">
              <div className="space-y-4">
                <img src="/bot-icon.png" className="w-20 h-20 mx-auto rounded-xl shadow-sm mb-2" alt="Bot" />
                <h2 className="text-2xl font-bold">How can I help you today?</h2>
                <div className="max-w-lg text-muted-foreground space-y-2">
                  <p>I am an advanced agentic Knowledge Bot.</p>
                  <p className="text-sm">
                    📚 <strong>RAG:</strong> Expert on <em>Rich Dad Poor Dad</em><br />
                    🌐 <strong>Web:</strong> Capable of crawling and searching the internet<br />
                    🤖 <strong>Tasks:</strong> Complex planning and reasoning
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl w-full px-4">
                {Object.entries(examples).map(([label, query]) => (
                  <button
                    key={label}
                    onClick={() => { setInput(query); }}
                    className="p-4 rounded-xl border bg-card hover:bg-accent hover:border-primary/50 text-left transition-all text-sm group shadow-sm hover:shadow-md"
                  >
                    <div className="font-semibold mb-1 group-hover:text-primary">{label}</div>
                    <div className="text-muted-foreground text-xs truncate">{query}</div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, idx) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "flex gap-4 max-w-4xl mx-auto",
                    msg.role === "assistant" ? "bg-muted/30 p-6 rounded-lg" : "px-6"
                  )}
                >
                  <div className="mt-1 shrink-0">
                    {msg.role === "assistant" ? (
                      <div className="w-9 h-9 rounded-full overflow-hidden border border-primary/20 bg-background">
                        <img src="/bot-icon.png" className="w-full h-full object-cover" alt="Bot" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                        <User className="w-5 h-5" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 space-y-2 overflow-hidden">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm">
                        {msg.role === "assistant" ? "Knowledge Bot" : "You"}
                      </span>
                      <span className="text-sm text-foreground/70">{msg.timestamp}</span>
                    </div>

                    <div className="prose dark:prose-invert max-w-none text-sm leading-relaxed">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>

                    {msg.role === "assistant" && msg.isStreaming && (
                      <div className="flex items-center gap-2 text-xs text-primary animate-pulse mt-2">
                        <Loader2 className="w-3 h-3 animate-spin" /> Thinking...
                      </div>
                    )}

                    {/* Footer: Routing Info & Feedback */}
                    {(msg.routing_decision || (msg.role === "assistant" && !msg.isStreaming)) && (
                      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">

                        {/* Routing Info */}
                        <div className="flex gap-2">
                          {msg.routing_decision && (
                            <span className="text-xs bg-accent px-2 py-1 rounded-full flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> {msg.routing_decision}
                            </span>
                          )}
                        </div>

                        {/* Feedback Buttons */}
                        {msg.role === "assistant" && !msg.isStreaming && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleFeedback(msg, "up", idx)}
                              className={cn(
                                "p-1 rounded hover:bg-background transition-colors",
                                msg.feedback === "up" ? "text-green-500" : "text-muted-foreground"
                              )}
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleFeedback(msg, "down", idx)}
                              className={cn(
                                "p-1 rounded hover:bg-background transition-colors",
                                msg.feedback === "down" ? "text-red-500" : "text-muted-foreground"
                              )}
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-border bg-background/95 backdrop-blur z-10">
          <div className="max-w-4xl mx-auto relative">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="relative flex items-center"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message Knowledge Bot..."
                className="w-full p-4 pr-12 rounded-xl border border-input bg-card focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="absolute right-3 p-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>
            <div className="text-center text-xs text-muted-foreground mt-2">
              Knowledge Bot can make mistakes. Consider checking important information.
            </div>
          </div>
        </div>

      </div>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {sessionToDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="bg-card border border-border rounded-xl shadow-lg max-w-sm w-full p-6 space-y-4"
            >
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-destructive" />
                Delete Session?
              </h3>
              <p className="text-muted-foreground text-sm">
                This action cannot be undone. The conversation history will be permanently removed.
              </p>
              <div className="flex justify-end gap-2 text-sm font-medium pt-2">
                <button
                  onClick={() => setSessionToDelete(null)}
                  className="px-4 py-2 rounded-lg hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (!sessionToDelete) return;
                    try {
                      await fetch(`${API_BASE_URL}/api/sessions/${sessionToDelete}`, { method: "DELETE" });
                      fetchSessions();
                      if (sessionId === sessionToDelete) {
                        clearChat();
                      }
                    } catch (err) {
                      console.error("Failed to delete", err);
                    } finally {
                      setSessionToDelete(null);
                    }
                  }}
                  className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
