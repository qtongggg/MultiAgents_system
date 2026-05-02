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
  | { role: "assistant"; type: "jobs"; jobs: Job[] }
  | { role: "assistant"; type: "list"; items: string[] };

export default function RagLandingPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const [uploading, setUploading] = useState(false);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // =========================
  // 🔥 CLEAN LIST FUNCTION
  // =========================
  function cleanAnswers(list: string[]) {
    if (!list || list.length === 0) return [];

    // remove duplicates
    const unique = Array.from(new Set(list));

    // remove empty / useless answers
    return unique.filter(
      (item) =>
        item &&
        item.trim() !== "" &&
        item !== "Not available in the provided resume context."
    );
  }

  // =========================
  // 🚀 SEND MESSAGE
  // =========================
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
      const rawAnswer = response?.data?.answer;

      // =========================
      // JOBS
      // =========================
      if (jobs.length > 0) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", type: "jobs", jobs },
        ]);
        setLoading(false);
        return;
      }

      // =========================
      // LIST RESPONSE (FIXED)
      // =========================
      if (Array.isArray(rawAnswer)) {
        const cleaned = cleanAnswers(rawAnswer);

        // 👉 If only ONE result → show as TEXT
        if (cleaned.length === 1) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              type: "text",
              content: cleaned[0],
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              type: "list",
              items: cleaned,
            },
          ]);
        }

        setLoading(false);
        return;
      }

      // =========================
      // TEXT RESPONSE
      // =========================
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content: rawAnswer ?? "No response found.",
        },
      ]);

      setLoading(false);
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

  // =========================
  // 📄 UPLOAD PDF
  // =========================
  async function handleFileUpload(file: File) {
    try {
      setUploading(true);

      await uploadPdf(file);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content: "✅ Resume uploaded successfully.",
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
          Ask anything about your resume or jobs
        </p>
      </div>

      {/* CHAT */}
      <div className="flex-1 overflow-y-auto px-6 mt-6 pb-28">
        <div className="max-w-5xl mx-auto space-y-6">

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

                {/* TEXT */}
                {msg.type === "text" && (
                  <div className="max-w-3xl">
                    <div
                      className={`px-4 py-2 rounded-2xl ${
                        msg.role === "user"
                          ? "bg-gray-900 text-white"
                          : "bg-white text-gray-800"
                      }`}
                    >
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* LIST (IMPROVED UI) */}
                {msg.type === "list" && (
                  <div className="space-y-2 max-w-3xl">
                    {msg.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="px-4 py-2 bg-white border rounded-xl text-gray-800 shadow-sm"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                )}

                {/* JOBS (unchanged) */}
                {msg.type === "jobs" && (
                  <div className="space-y-4 w-full">
                    {msg.jobs.map((job, j) => (
                      <motion.div
                        key={j}
                        whileHover={{ scale: 1.02, y: -4 }}
                        className="rounded-xl p-4 bg-white border space-y-3"
                      >
                        <p className="font-semibold">{job.title}</p>
                        <p className="text-sm text-gray-500">
                          {job.company} • {job.location}
                        </p>
                      </motion.div>
                    ))}
                  </div>
                )}

              </motion.div>
            ))}
          </AnimatePresence>

          {loading && <p className="text-sm text-gray-400">Thinking...</p>}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* INPUT */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
        <div className="flex items-center gap-2 bg-white border rounded-full px-3 py-2">

          {/* UPLOAD */}
          <label className="cursor-pointer p-2">
            <Paperclip size={16} />
            <input
              type="file"
              hidden
              accept=".pdf"
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
            placeholder="Ask anything..."
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSend(input);
                setInput("");
              }
            }}
          />

          {/* SEND */}
          <button
            onClick={() => {
              handleSend(input);
              setInput("");
            }}
            className="p-2 bg-gray-900 text-white rounded-full"
          >
            <ArrowRight size={16} />
          </button>

        </div>

        {uploading && (
          <p className="text-xs text-gray-500 mt-1">
            Uploading resume...
          </p>
        )}
      </div>
    </main>
  );
}