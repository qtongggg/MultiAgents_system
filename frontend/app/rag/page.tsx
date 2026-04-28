"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { askRagQuestion } from "@/lib/api";
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

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // 🔥 Suggestion Cards
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

  return (
    <main className="flex flex-col h-screen bg-[#f5f5f5] text-gray-900">

      {/* Header */}
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

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-6 mt-6 pb-28">
        <div className="max-w-5xl mx-auto space-y-6">

          {/* 🔥 EMPTY STATE (Homepage UI) */}
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
                    onClick={() => {
                      setInput(card.prompt);
                      handleSend(card.prompt);
                    }}
                    className="cursor-pointer rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm hover:shadow-md transition"
                  >
                    <p className="font-medium text-gray-900">{card.title}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {card.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* 🔥 CHAT */}
          {messages.length > 0 && (
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
                        className={`inline-block px-4 py-2 rounded-2xl ${
                          msg.role === "user"
                            ? "bg-gray-900 text-white ml-auto"
                            : "text-gray-800"
                        }`}
                      >
                        <div className="prose max-w-none">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* JOBS */}
                  {msg.type === "jobs" && (
                    <div className="space-y-4 w-full">
                      {msg.jobs.map((job, j) => (
                        <motion.div
                          key={j}
                          whileHover={{ scale: 1.02, y: -4 }}
                          className="rounded-xl p-4 bg-white border border-gray-200 space-y-3"
                        >
                          {/* Header */}
                          <div className="flex justify-between">
                            <div>
                              <p className="font-semibold">{job.title}</p>
                              <p className="text-sm text-gray-500">
                                {job.company} • {job.location}
                              </p>
                            </div>

                            {job.link && (
                              <a
                                href={job.link}
                                target="_blank"
                                className="text-sm px-3 py-1 rounded-full bg-gray-900 text-white hover:bg-gray-700"
                              >
                                Apply
                              </a>
                            )}
                          </div>

                          {/* Reason */}
                          {job.reason && (
                            <p className="text-sm text-gray-600">
                              {job.reason}
                            </p>
                          )}

                          {/* Matching Skills */}
                          {job.matching_skills && (
                            <div>
                              <p className="text-xs text-gray-500 mb-1">
                                Matching Skills
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {job.matching_skills.map((s, i) => (
                                  <span
                                    key={i}
                                    className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Missing Skills */}
                          {job.missing_skills && (
                            <div>
                              <p className="text-xs text-gray-500 mb-1">
                                Missing Skills
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {job.missing_skills.map((s, i) => (
                                  <span
                                    key={i}
                                    className="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded-full"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Score */}
                          {job.fit_score !== undefined && (
                            <div>
                              <p className="text-xs text-gray-600 mb-1">
                                Match: {Math.round(job.fit_score * 100)}%
                              </p>
                              <div className="h-2 bg-gray-200 rounded-full">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{
                                    width: `${job.fit_score * 100}%`,
                                  }}
                                  className="h-full bg-gray-900"
                                />
                              </div>
                            </div>
                          )}
                        </motion.div>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {/* Loader */}
          {loading && (
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="w-2 h-2 bg-gray-400 rounded-full"
                  animate={{ y: [0, -6, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
        <div className="flex items-center gap-2 rounded-full border bg-white px-3 py-2 shadow-sm">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 outline-none text-sm"
          />
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
      </div>
    </main>
  );
}