"use client";

import { useEffect, useRef, useState } from "react";
import RagQueryForm from "@/components/RagQueryForm";
import { askRagQuestion } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { motion } from "framer-motion";

// -------------------------
// TYPES
// -------------------------
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

// -------------------------
// COMPONENT
// -------------------------
export default function RagPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      type: "text",
      content: "Hello! Upload a PDF, then ask me anything about its content.",
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // -------------------------
  // SEND MESSAGE
  // -------------------------

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
          err instanceof Error
            ? err.message
            : "Something went wrong.",
      };

      setMessages((prev) => [...prev, errorMessage]);
      setError("Failed to get response.");
    } finally {
      setLoading(false);
    }
  }



  // -------------------------
  // FILE HANDLING
  // -------------------------
  function handleUploadStart(fileName: string) {
    setMessages((prev) => [
      ...prev,
      { role: "user", type: "file", fileName },
      {
        role: "assistant",
        type: "text",
        content: `Uploading ${fileName}...`,
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
          msg.content.startsWith("Uploading ")
        ) {
          return {
            ...msg,
            content: `Uploaded ${fileName}. You can now ask questions about it.`,
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
          msg.content.startsWith("Uploading ")
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

  // -------------------------
  // RENDER
  // -------------------------
  return (
    <main className="min-h-screen bg-[#F3F3F3] text-[#2B2B2B]">
      <div className="mx-auto flex h-screen max-w-6xl gap-6 p-6">
        <section className="flex flex-1 flex-col rounded-[32px] border bg-white shadow-sm">
          
          {/* Header */}
          <div className="border-b px-6 py-5">
            <h2 className="text-xl font-semibold">Document Chat</h2>
            <p className="text-sm text-gray-500">
              Ask questions about your uploaded PDF
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
            {messages.map((msg, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm shadow ${
                    msg.role === "user"
                      ? "bg-black text-white"
                      : "bg-white border"
                  }`}
                >
                  {/* FILE */}
                  {msg.type === "file" && (
                    <button
                      disabled={!msg.fileUrl}
                      onClick={() =>
                        msg.fileUrl && setPreviewUrl(msg.fileUrl)
                      }
                    >
                      📄 {msg.fileName}
                    </button>
                  )}

                  {/* JOBS */}
                  {msg.type === "jobs" && (
                    <div className="space-y-4">
                      <p className="text-xs text-gray-500">
                        Found {msg.jobs.length} jobs
                      </p>

                      {msg.jobs.map((job, i) => (
                        <div
                          key={i}
                          className="border rounded-xl p-4 hover:shadow-md transition"
                        >
                          <p className="font-semibold">{job.title}</p>
                          <p className="text-xs text-gray-500">
                            {job.company} • {job.location}
                          </p>

                          {job.fit_score !== undefined && (
                            <div className="mt-2">
                              <div className="h-2 bg-gray-200 rounded-full">
                                <div
                                  className="h-2 bg-green-500 rounded-full"
                                  style={{
                                    width: `${Math.round(
                                      job.fit_score * 100
                                    )}%`,
                                  }}
                                />
                              </div>
                              <p className="text-xs mt-1">
                                Match:{" "}
                                {Math.round(job.fit_score * 100)}%
                              </p>
                            </div>
                          )}

                          {job.matching_skills && job.matching_skills.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs text-gray-500">Matching Skills:</p>
                              <ul className="text-xs list-disc list-inside">
                                {job.matching_skills.map((skill, i) => (
                                  <li key={i}>{skill}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {job.missing_skills && job.missing_skills.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs text-red-500">Missing Skills:</p>
                              <ul className="text-xs list-disc list-inside">
                                {job.missing_skills.map((skill, i) => (
                                  <li key={i}>{skill}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {job.link && (
                            <a
                              href={job.link}
                              target="_blank"
                              className="text-xs text-blue-600 mt-2 inline-block"
                            >
                              View Job →
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
                          <p className="mb-2">{children}</p>
                        ),
                        code({
                          inline,
                          className,
                          children,
                          ...props
                        }) {
                          const match =
                            /language-(\w+)/.exec(className || "");

                          if (!inline && match) {
                            return (
                              <div className="relative">
                                <button
                                  onClick={() =>
                                    navigator.clipboard.writeText(
                                      String(children)
                                    )
                                  }
                                  className="absolute right-2 top-2 bg-gray-700 text-white px-2 py-1 text-xs rounded"
                                >
                                  Copy
                                </button>

                                <SyntaxHighlighter
                                  style={oneDark}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, "")}
                                </SyntaxHighlighter>
                              </div>
                            );
                          }

                          return (
                            <code className="bg-gray-200 px-1 rounded">
                              {children}
                            </code>
                          );
                        },
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>
              </motion.div>
            ))}

            {/* Loading */}
            {loading && (
              <div className="flex">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-300" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t px-6 py-4">
            <RagQueryForm
              onSend={handleSend}
              loading={loading}
              onUploadStart={handleUploadStart}
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <p className="text-red-500 text-sm mt-2">{error}</p>
            )}
          </div>
        </section>
      </div>

      {/* PDF Preview */}
      {previewUrl && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="w-[90%] h-[90%] bg-white rounded-xl">
            <button onClick={() => setPreviewUrl(null)}>
              Close
            </button>
            <iframe src={previewUrl} className="w-full h-full" />
          </div>
        </div>
      )}
    </main>
  );
}