"use client";

import { useEffect, useRef, useState } from "react";
import RagQueryForm from "@/components/RagQueryForm";
import { askRagQuestion } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// ============================================================================
// TYPES
// ============================================================================

type Job = {
  title: string;
  company: string;
  location: string;
  link?: string;
  fit_score?: number;
  missing_skills?: string[];
  matching_skills?: string[];
};

type BaseMessage = {
  role: "user" | "assistant";
};

type TextMessage = BaseMessage & {
  type: "text";
  content: string;
};

type JobsMessage = BaseMessage & {
  role: "assistant";
  type: "jobs";
  jobs: Job[];
};

type FileMessage = BaseMessage & {
  type: "file";
  fileName: string;
  fileUrl?: string;
};

type Message = TextMessage | JobsMessage | FileMessage;

// ============================================================================
// COMPONENT
// ============================================================================

export default function RagPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      type: "text",
      content: "Hey! 👋 Upload a PDF to get started, then ask me anything about its content.",
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ============================================================================
  // HANDLERS
  // ============================================================================

  async function handleSend(question: string) {
    const userMessage: TextMessage = {
      role: "user",
      type: "text",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError("");

    try {
      const response = await askRagQuestion(question, 5);

      const jobs = response?.data?.jobs ?? [];
      const answer = response?.data?.answer ?? "";

      if (jobs.length > 0) {
        const assistantMessage: JobsMessage = {
          role: "assistant",
          type: "jobs",
          jobs: jobs,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        const assistantMessage: TextMessage = {
          role: "assistant",
          type: "text",
          content: answer || "No answer returned.",
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (err) {
      const errorMessage: TextMessage = {
        role: "assistant",
        type: "text",
        content:
          err instanceof Error ? err.message : "Something went wrong.",
      };

      setMessages((prev) => [...prev, errorMessage]);
      setError("Failed to get response.");
    } finally {
      setLoading(false);
    }
  }

  function handleUploadStart(fileName: string) {
    setMessages((prev) => [
      ...prev,
      { role: "user", type: "file", fileName },
      {
        role: "assistant",
        type: "text",
        content: `Processing ${fileName}...`,
      },
    ]);
  }

  function handleUploadSuccess(fileName: string, fileUrl: string) {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.type === "file" && !msg.fileUrl) {
          return { ...msg, fileUrl };
        }

        if (
          msg.type === "text" &&
          msg.content.startsWith("Processing ")
        ) {
          return {
            ...msg,
            content: `✅ Successfully uploaded **${fileName}**. You can now ask questions about it.`,
          };
        }

        return msg;
      })
    );
  }

  function handleUploadError(fileName: string) {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.type === "file" && !msg.fileUrl) {
          return {
            ...msg,
            fileName: `${fileName} (upload failed)`,
          };
        }

        if (
          msg.type === "text" &&
          msg.content.startsWith("Processing ")
        ) {
          return {
            ...msg,
            content: `Failed to upload ${fileName}. Please try again.`,
          };
        }

        return msg;
      })
    );
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <main className="min-h-screen bg-gradient-to-b from-[#FAFAFA] to-[#F5F5F5]">
      <div className="mx-auto flex h-screen max-w-4xl flex-col px-4 py-6">
        
        {/* Header */}
        <header className="mb-6 space-y-2">
          <h1 className="text-3xl font-semibold text-[#1a1a1a] tracking-tight">
            Document Chat
          </h1>
          <p className="text-sm text-[#666] font-light">
            Ask questions about your PDF. Get instant answers powered by AI.
          </p>
        </header>

        {/* Chat Container */}
        <section className="flex-1 flex flex-col rounded-2xl border border-[#E5E5E5] bg-white shadow-sm overflow-hidden">
          
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-4 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
                style={{
                  animation: 'fadeInSlide 0.3s ease-out',
                }}
              >
                {/* Avatar */}
                {msg.role === "assistant" && (
                  <div className="mt-1 h-8 w-8 flex-shrink-0 rounded-full bg-gradient-to-br from-[#2B2B2B] to-[#4a4a4a] flex items-center justify-center text-white text-sm font-medium">
                    AI
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`flex-1 max-w-xl ${
                    msg.role === "user" ? "text-right" : ""
                  }`}
                >
                  <div
                    className={`inline-block px-5 py-3 rounded-xl text-[15px] leading-relaxed ${
                      msg.role === "user"
                        ? "bg-[#2B2B2B] text-white rounded-br-none"
                        : "bg-[#F8F8F8] text-[#2B2B2B] rounded-bl-none border border-[#E5E5E5]"
                    }`}
                  >
                    {/* FILE */}
                    {msg.type === "file" && (
                      <button
                        disabled={!msg.fileUrl}
                        onClick={() =>
                          msg.fileUrl && setPreviewUrl(msg.fileUrl)
                        }
                        className={`flex items-center gap-2 font-medium transition ${
                          msg.fileUrl
                            ? "text-blue-600 hover:text-blue-700 cursor-pointer"
                            : "text-gray-400 cursor-not-allowed"
                        }`}
                      >
                        <span className="text-lg">📄</span>
                        <span className="underline">{msg.fileName}</span>
                      </button>
                    )}

                    {/* JOBS */}
                    {msg.type === "jobs" && (
                      <div className="space-y-3">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Found {msg.jobs.length} matching job{msg.jobs.length !== 1 ? "s" : ""}
                        </p>

                        {msg.jobs.map((job, i) => (
                          <div
                            key={i}
                            className="border border-[#E5E5E5] rounded-lg p-4 bg-white hover:border-[#2B2B2B] hover:shadow-sm transition"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-[#2B2B2B] truncate">
                                  {job.title}
                                </h3>
                                <p className="text-xs text-[#666] mt-1">
                                  {job.company} • {job.location}
                                </p>
                              </div>

                              {job.fit_score !== undefined && (
                                <div className="flex-shrink-0 text-right">
                                  <div className="inline-flex items-center gap-2 bg-green-50 px-3 py-1 rounded-full border border-green-200">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-green-400 to-green-500 flex items-center justify-center text-white text-xs font-bold">
                                      {Math.round(job.fit_score * 100)}
                                    </div>
                                    <span className="text-xs font-medium text-green-700">Match</span>
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Skills Section */}
                            <div className="mt-3 space-y-2">
                              {job.matching_skills && job.matching_skills.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-600 mb-1.5">
                                    ✓ Matching Skills
                                  </p>
                                  <div className="flex flex-wrap gap-1.5">
                                    {job.matching_skills.map((skill, i) => (
                                      <span
                                        key={i}
                                        className="inline-block px-2.5 py-1 bg-green-100 text-green-700 text-xs rounded-md font-medium"
                                      >
                                        {skill}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {job.missing_skills && job.missing_skills.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-600 mb-1.5">
                                    ○ Missing Skills
                                  </p>
                                  <div className="flex flex-wrap gap-1.5">
                                    {job.missing_skills.map((skill, i) => (
                                      <span
                                        key={i}
                                        className="inline-block px-2.5 py-1 bg-red-50 text-red-600 text-xs rounded-md font-medium border border-red-200"
                                      >
                                        {skill}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>

                            {job.link && (
                              <a
                                href={job.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 mt-3 text-xs font-semibold text-blue-600 hover:text-blue-700 transition"
                              >
                                View Job
                                <span className="text-sm">→</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* TEXT */}
                    {msg.type === "text" && (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => (
                            <p className="mb-2 last:mb-0">{children}</p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc list-inside mb-2 space-y-1 text-sm">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal list-inside mb-2 space-y-1 text-sm">
                              {children}
                            </ol>
                          ),
                          strong: ({ children }) => (
                            <strong className="font-semibold">{children}</strong>
                          ),
                          em: ({ children }) => (
                            <em className="italic">{children}</em>
                          ),
                          code({ inline, className, children, ...props }) {
                            const match = /language-(\w+)/.exec(className || "");

                            if (!inline && match) {
                              return (
                                <div className="relative my-2 rounded-lg overflow-hidden">
                                  <button
                                    onClick={() =>
                                      navigator.clipboard.writeText(
                                        String(children)
                                      )
                                    }
                                    className="absolute right-3 top-3 bg-gray-700 hover:bg-gray-800 text-white px-2.5 py-1.5 text-xs rounded font-medium transition z-10"
                                  >
                                    Copy
                                  </button>

                                  <SyntaxHighlighter
                                    style={oneDark}
                                    language={match[1]}
                                    PreTag="div"
                                    className="!bg-gray-900 !mt-0 !rounded-lg"
                                    {...props}
                                  >
                                    {String(children).replace(/\n$/, "")}
                                  </SyntaxHighlighter>
                                </div>
                              );
                            }

                            return (
                              <code className="bg-gray-200 px-1.5 py-0.5 rounded font-mono text-sm text-[#d63384]">
                                {children}
                              </code>
                            );
                          },
                          blockquote: ({ children }) => (
                            <blockquote className="border-l-4 border-gray-300 pl-3 italic text-gray-600 my-2">
                              {children}
                            </blockquote>
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    )}
                  </div>
                </div>

                {/* User Avatar */}
                {msg.role === "user" && (
                  <div className="mt-1 h-8 w-8 flex-shrink-0 rounded-full bg-[#2B2B2B] flex items-center justify-center text-white text-sm font-medium">
                    U
                  </div>
                )}
              </div>
            ))}

            {/* Loading Indicator */}
            {loading && (
              <div 
                className="flex gap-4"
                style={{
                  animation: 'fadeInSlide 0.3s ease-out',
                }}
              >
                <div className="mt-1 h-8 w-8 flex-shrink-0 rounded-full bg-gradient-to-br from-[#2B2B2B] to-[#4a4a4a] flex items-center justify-center text-white text-sm font-medium">
                  AI
                </div>
                <div className="flex gap-1.5 items-center">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }} />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-[#E5E5E5] px-6 py-5 bg-white">
            <RagQueryForm
              onSend={handleSend}
              loading={loading}
              onUploadStart={handleUploadStart}
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <p className="text-red-500 text-sm mt-3">{error}</p>
            )}
          </div>
        </section>
      </div>

      {/* PDF Preview Modal */}
      {previewUrl && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full h-[90vh] max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E5E5]">
              <h3 className="font-semibold text-[#2B2B2B]">PDF Preview</h3>
              <button
                onClick={() => setPreviewUrl(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl transition"
              >
                ✕
              </button>
            </div>
            <iframe
              src={previewUrl}
              className="w-full flex-1"
            />
          </div>
        </div>
      )}
    </main>
  );
}