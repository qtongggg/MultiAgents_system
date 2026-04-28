"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Paperclip } from "lucide-react";
import { askRagQuestion, uploadPdf } from "@/lib/api";
import ReactMarkdown from "react-markdown";

type Job = {
  title: string;
  company: string;
  location: string;
  fit_score?: number;
  reason?: string;
  matching_skills?: string[];
  missing_skills?: string[];
  link?: string;
};

type Message =
  | { role: "user"; type: "text"; content: string }
  | { role: "assistant"; type: "text"; content: string }
  | { role: "assistant"; type: "jobs"; jobs: Job[] };

export default function RagLandingPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  // 🔥 Upload states
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // 🔥 Suggestions
  const suggestionCards = [
    {
      title: "📄 Review my resume",
      description: "Get feedback and improve your CV",
      prompt: "Can you review my resume and suggest improvements?",
    },
    {
      title: "🔍 Find matching jobs",
      description: "Based on your skills and experience",
      prompt: "Find jobs that match my resume",
    },
    {
      title: "🧠 Missing skills",
      description: "Identify skill gaps for your target role",
      prompt: "What skills are missing in my CV?",
    },
    {
      title: "📧 Send jobs to email",
      description: "Receive job recommendations via email",
      prompt: "Find jobs and send them to my email",
    },
  ];

  // 🔥 HANDLE CHAT
  async function handleSend(question: string) {
    if (!question.trim()) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", type: "text", content: question },
    ]);

    setLoading(true);

    try {
      const response = await askRagQuestion(question, 5);

      const jobs = response?.data?.jobs ?? [];
      const answer = response?.data?.answer ?? "";

      if (jobs.length > 0) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", type: "jobs", jobs },
        ]);
        setLoading(false);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", type: "text", content: "" },
        ]);

        const words = answer.split(" ");
        let i = 0;

        const interval = setInterval(() => {
          i++;

          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (!last || last.type !== "text") return prev;

            const updated = [...prev];
            updated[updated.length - 1] = {
              ...last,
              content: words.slice(0, i).join(" "),
            };

            return updated;
          });

          if (i >= words.length) {
            clearInterval(interval);
            setLoading(false);
          }
        }, 40);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content: "Something went wrong.",
        },
      ]);
      setLoading(false);
    }
  }

  // 🔥 HANDLE PDF UPLOAD
  async function handleFileUpload(selectedFile: File) {
    try {
      setUploading(true);
      setFile(selectedFile);

      await uploadPdf(selectedFile);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content:
            "✅ Resume uploaded successfully. You can now ask questions about it.",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content: "❌ Upload failed.",
        },
      ]);
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="flex flex-col h-screen bg-[#f5f5f5] text-gray-900">

      {/* HEADER */}
      <div className="text-center pt-8 px-6">
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-semibold"
        >
          AI Career Copilot
        </motion.h1>

        <p className="mt-2 text-gray-500">
          Ask anything about your resume or job search
        </p>
      </div>

      {/* CHAT */}
      <div className="flex-1 overflow-y-auto px-6 mt-6 pb-32">
        <div className="max-w-5xl mx-auto space-y-6">

          {/* EMPTY STATE */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center mt-20 text-center">
              <h2 className="text-2xl font-semibold text-gray-800">
                What can I help you with?
              </h2>

              <p className="text-gray-500 mt-2 mb-6">
                Try one of the suggestions below
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
                {suggestionCards.map((card, i) => (
                  <motion.div
                    key={i}
                    whileHover={{ scale: 1.03, y: -4 }}
                    onClick={() => handleSend(card.prompt)}
                    className="cursor-pointer rounded-xl border bg-white p-4 shadow-sm hover:shadow-md"
                  >
                    <p className="font-medium">{card.title}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {card.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* MESSAGES */}
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.type === "text" && (
                  <div className="max-w-3xl">
                    <div
                      className={`px-4 py-2 rounded-2xl ${
                        msg.role === "user"
                          ? "bg-gray-900 text-white"
                          : "text-gray-800"
                      }`}
                    >
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {msg.type === "jobs" && (
                  <div className="space-y-4 w-full">
                    {msg.jobs.map((job, j) => (
                      <div key={j} className="rounded-xl p-4 bg-white border">
                        <p className="font-semibold">{job.title}</p>
                        <p className="text-sm text-gray-500">
                          {job.company} • {job.location}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {/* LOADING */}
          {loading && <p className="text-sm text-gray-400">Thinking...</p>}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* INPUT + UPLOAD */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
        <div className="flex flex-col gap-2 rounded-2xl border bg-white px-3 py-2 shadow-sm">

          {/* FILE PREVIEW */}
          {file && (
            <div className="flex justify-between bg-gray-100 px-3 py-1 rounded-lg text-sm">
              <span>{file.name}</span>
              <button onClick={() => setFile(null)} className="text-red-500">
                remove
              </button>
            </div>
          )}

          <div className="flex items-center gap-2">

            {/* UPLOAD */}
            <label className="cursor-pointer p-2 hover:bg-gray-100 rounded-full">
              <Paperclip size={16} />
              <input
                type="file"
                accept=".pdf"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f);
                }}
              />
            </label>

            {/* INPUT */}
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 outline-none text-sm"
              placeholder="Ask about your resume..."
            />

            {/* SEND */}
            <button
              onClick={() => {
                handleSend(input);
                setInput("");
              }}
              disabled={uploading}
              className="p-2 bg-gray-900 text-white rounded-full"
            >
              <ArrowRight size={16} />
            </button>
          </div>

          {uploading && (
            <p className="text-xs text-gray-500">Uploading resume...</p>
          )}
        </div>
      </div>
    </main>
  );
}