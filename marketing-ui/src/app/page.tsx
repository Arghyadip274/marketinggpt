"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Menu, X, Sparkles } from "lucide-react";
import axios from "axios";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

type Message = {
  role: "user" | "assistant";
  content: string;
};

type Persona = {
  name: string;
  greeting: string;
};

const API_BASE = "http://127.0.0.1:8000/api";

export default function Home() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [activePersona, setActivePersona] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch personas on mount
  useEffect(() => {
    axios.get(`${API_BASE}/personas`)
      .then((res) => {
        const data = res.data.personas;
        setPersonas(data);
        if (data.length > 0) {
          handlePersonaChange(data[0]);
        }
      })
      .catch((err) => console.error("Failed to load personas:", err));
  }, []);

  const handlePersonaChange = (persona: Persona) => {
    setActivePersona(persona.name);
    setMessages([{ role: "assistant", content: persona.greeting }]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const newMessages: Message[] = [...messages, { role: "user", content: input.trim() }];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, {
        messages: newMessages,
        active_persona: activePersona
      });
      
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Sorry, I encountered an error connecting to the server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] font-sans overflow-hidden selection:bg-blue-500/30">
      
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Glassmorphism */}
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: sidebarOpen ? 0 : -300 }}
        transition={{ type: "spring", bounce: 0, duration: 0.4 }}
        className={cn(
          "fixed md:relative z-50 h-full w-72 flex flex-col border-r border-white/10",
          "bg-[#161b22]/80 backdrop-blur-xl shadow-2xl"
        )}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Sparkles className="w-5 h-5 text-blue-400" />
            </div>
            <h1 className="font-semibold tracking-tight text-white">MarketingGPT</h1>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="md:hidden text-white/50 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 flex-1 overflow-y-auto">
          <h2 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">Select Persona</h2>
          <div className="space-y-2">
            {personas.map((p) => (
              <button
                key={p.name}
                onClick={() => handlePersonaChange(p)}
                className={cn(
                  "w-full text-left px-4 py-3 rounded-xl transition-all duration-200 group flex items-center gap-3",
                  activePersona === p.name 
                    ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" 
                    : "hover:bg-white/5 text-white/60 hover:text-white border border-transparent"
                )}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  activePersona === p.name ? "bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" : "bg-white/20 group-hover:bg-white/40"
                )} />
                <span className="truncate text-sm font-medium">{p.name}</span>
              </button>
            ))}
          </div>
        </div>
      </motion.aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col h-full relative">
        {/* Header */}
        <header className="absolute top-0 w-full p-4 flex items-center justify-between z-10 bg-gradient-to-b from-[#0d1117] to-transparent">
          <button 
            onClick={() => setSidebarOpen(true)}
            className={cn("p-2 text-white/50 hover:text-white transition-colors rounded-lg hover:bg-white/5", sidebarOpen && "md:hidden")}
          >
            <Menu className="w-6 h-6" />
          </button>
        </header>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 pt-20 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-8">
            <AnimatePresence initial={false}>
              {messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    "flex w-full gap-4",
                    msg.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-[#161b22] border border-white/10 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                      <Bot className="w-4 h-4 text-white/70" />
                    </div>
                  )}
                  
                  <div className={cn(
                    "px-5 py-3.5 max-w-[85%] leading-relaxed text-[15px] shadow-sm",
                    msg.role === "user" 
                      ? "bg-gradient-to-br from-blue-600 to-blue-500 text-white rounded-2xl rounded-tr-sm shadow-blue-500/10"
                      : "bg-[#161b22]/80 backdrop-blur-md border border-white/5 rounded-2xl rounded-tl-sm text-white/90"
                  )}>
                    {msg.role === "user" ? (
                      msg.content.split('\n').map((line, i) => (
                        <span key={i}>
                          {line}
                          {i !== msg.content.split('\n').length - 1 && <br />}
                        </span>
                      ))
                    ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({node, ...props}) => <h1 className="text-2xl font-bold text-white mb-4 mt-6 border-b border-white/10 pb-2" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-xl font-bold text-white mb-3 mt-5" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-lg font-semibold text-white/90 mb-3 mt-4" {...props} />,
                          p: ({node, ...props}) => <p className="mb-4 last:mb-0 leading-relaxed text-white/80" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-4 space-y-1 text-white/80" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-4 space-y-1 text-white/80" {...props} />,
                          li: ({node, ...props}) => <li className="pl-1" {...props} />,
                          strong: ({node, ...props}) => <strong className="font-semibold text-white bg-white/5 px-1 rounded" {...props} />,
                          table: ({node, ...props}) => (
                            <div className="overflow-x-auto mb-4 border border-white/10 rounded-xl shadow-lg bg-black/20">
                              <table className="w-full text-left border-collapse text-sm" {...props} />
                            </div>
                          ),
                          th: ({node, ...props}) => <th className="p-3 border-b border-white/10 font-medium text-white/90 bg-white/5 uppercase tracking-wider text-xs" {...props} />,
                          td: ({node, ...props}) => <td className="p-3 border-b border-white/5 text-white/70" {...props} />,
                          tr: ({node, ...props}) => <tr className="hover:bg-white/[0.02] transition-colors" {...props} />,
                          a: ({node, ...props}) => <a className="text-blue-400 hover:text-blue-300 underline underline-offset-4 decoration-blue-500/30" {...props} />,
                          code: ({node, inline, className, children, ...props}: any) => {
                            if (!inline && className === 'language-recharts') {
                              try {
                                const data = JSON.parse(String(children).replace(/\n$/, ''));
                                const keys = Object.keys(data[0] || {}).filter(k => k !== 'name');
                                const dataKey = keys[0] || 'value';
                                return (
                                  <div className="h-64 w-full my-6 p-4 bg-[#0d1117] rounded-xl border border-white/10">
                                    <ResponsiveContainer width="100%" height="100%">
                                      <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                        <XAxis dataKey="name" stroke="#ffffff50" fontSize={11} tickLine={false} axisLine={false} />
                                        <YAxis stroke="#ffffff50" fontSize={11} tickLine={false} axisLine={false} />
                                        <Tooltip 
                                          cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                          contentStyle={{ backgroundColor: '#161b22', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                                          itemStyle={{ color: '#3b82f6', fontWeight: 'bold' }}
                                        />
                                        <Bar dataKey={dataKey} fill="url(#blueGradient)" radius={[4, 4, 0, 0]} />
                                        <defs>
                                          <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#3b82f6" />
                                            <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0.8} />
                                          </linearGradient>
                                        </defs>
                                      </BarChart>
                                    </ResponsiveContainer>
                                  </div>
                                );
                              } catch (e) {
                                return <div className="p-4 bg-red-500/10 text-red-400 rounded-xl mb-4 text-sm font-mono border border-red-500/20">Chart Parse Error: Invalid JSON</div>;
                              }
                            }
                            return inline 
                              ? <code className="bg-white/10 text-blue-300 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>{children}</code>
                              : <pre className="bg-[#0d1117] p-4 rounded-xl border border-white/10 overflow-x-auto text-sm font-mono text-white/80 mb-4"><code className={className} {...props}>{children}</code></pre>;
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    )}
                  </div>

                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center shrink-0 mt-1">
                      <User className="w-4 h-4 text-blue-400" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading Indicator */}
            {isLoading && (
              <motion.div 
                initial={{ opacity: 0 }} 
                animate={{ opacity: 1 }} 
                className="flex w-full gap-4 justify-start"
              >
                <div className="w-8 h-8 rounded-full bg-[#161b22] border border-white/10 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-white/50" />
                </div>
                <div className="px-5 py-4 bg-[#161b22]/50 backdrop-blur-md border border-white/5 rounded-2xl rounded-tl-sm flex gap-1.5 items-center">
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0 }} className="w-1.5 h-1.5 bg-white/40 rounded-full" />
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-1.5 h-1.5 bg-white/40 rounded-full" />
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-1.5 h-1.5 bg-white/40 rounded-full" />
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 bg-gradient-to-t from-[#0d1117] via-[#0d1117] to-transparent">
          <div className="max-w-3xl mx-auto relative">
            <form 
              onSubmit={handleSubmit}
              className="relative flex items-end gap-2 bg-[#161b22] border border-white/10 rounded-3xl shadow-2xl p-2 transition-all focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/50"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message MarketingGPT..."
                className="w-full max-h-48 bg-transparent border-none text-white placeholder-white/30 focus:ring-0 resize-none py-3 px-4 outline-none text-[15px]"
                rows={1}
                style={{ minHeight: "48px" }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  "p-3 rounded-full flex shrink-0 transition-all",
                  input.trim() && !isLoading
                    ? "bg-blue-500 hover:bg-blue-400 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                    : "bg-white/5 text-white/30 cursor-not-allowed"
                )}
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
            <p className="text-center text-[11px] text-white/30 mt-3 font-medium">
              MarketingGPT can make mistakes. Consider verifying important information.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
