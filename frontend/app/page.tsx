// app/page.tsx  (or wherever your page lives)
"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FileText, Briefcase, ArrowRight } from "lucide-react";
import { MatrixText } from "@/components/ui/matrix-text";

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050d14] text-white">

      {/* Grid background */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,255,157,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,157,0.03) 1px,transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Ambient glows */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute left-1/2 top-0 h-[500px] w-[600px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(0,255,157,0.08)_0%,transparent_70%)]" />
        <div className="absolute -left-20 bottom-0 h-[400px] w-[400px] rounded-full bg-[radial-gradient(circle,rgba(0,180,255,0.06)_0%,transparent_70%)]" />
        <div className="absolute -right-16 top-48 h-[300px] w-[300px] rounded-full bg-[radial-gradient(circle,rgba(120,60,255,0.05)_0%,transparent_70%)]" />
      </div>

      <div className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">

        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-8 inline-flex w-fit items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/5 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-emerald-400/80"
        >
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          AI-Powered HR Workflow System
        </motion.div>

        {/* Hero — MatrixText replaces the plain h1 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
        >
          <MatrixText
            text="HR AI Agent"
            initialDelay={300}
            letterAnimationDuration={500}
            letterInterval={90}
            // Override the default min-h-screen centering so it sits in the flow
            className="!min-h-0 !items-start !justify-start text-[clamp(40px,8vw,72px)] font-extrabold"
          />
        </motion.div>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="mb-12 max-w-xl font-mono text-sm leading-relaxed text-slate-500"
        >
          {`// Streamline resume ingestion, document Q&A, and`}
          <br />
          {`intelligent job search with agentic AI workflows.`}
        </motion.p>

        {/* Cards */}
        <div className="grid gap-5 md:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.55, duration: 0.6 }}
          >
            <Link
              href="/rag"
              className="group relative block overflow-hidden rounded-2xl border border-white/7 bg-white/[0.03] p-7 transition-all duration-300 hover:-translate-y-1 hover:border-emerald-400/20 hover:bg-white/5"
            >
              <span className="absolute right-5 top-5 font-mono text-[10px] tracking-widest text-white/15">
                01 / RAG
              </span>
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-[14px] border border-emerald-400/15 bg-emerald-400/10 text-emerald-400">
                <FileText className="h-5 w-5" />
              </div>
              <h2 className="mb-2.5 text-xl font-bold text-slate-200">RAG PDF</h2>
              <p className="mb-6 font-mono text-[13px] leading-relaxed text-slate-600">
                Upload a PDF, process its content, and ask contextual questions
                using retrieval-augmented generation.
              </p>
              <span className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-400 transition-all group-hover:gap-3">
                Open module <ArrowRight className="h-4 w-4" />
              </span>
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.6 }}
          >
            <Link
              href="/jobs"
              className="group relative block overflow-hidden rounded-2xl border border-white/7 bg-white/[0.03] p-7 transition-all duration-300 hover:-translate-y-1 hover:border-sky-400/20 hover:bg-white/5"
            >
              <span className="absolute right-5 top-5 font-mono text-[10px] tracking-widest text-white/15">
                02 / JOBS
              </span>
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-[14px] border border-sky-400/15 bg-sky-400/10 text-sky-400">
                <Briefcase className="h-5 w-5" />
              </div>
              <h2 className="mb-2.5 text-xl font-bold text-slate-200">Job Search Agent</h2>
              <p className="mb-6 font-mono text-[13px] leading-relaxed text-slate-600">
                Search jobs, summarize positions, and rank opportunities against
                your resume with AI assistance.
              </p>
              <span className="inline-flex items-center gap-2 text-sm font-semibold text-sky-400 transition-all group-hover:gap-3">
                Explore jobs <ArrowRight className="h-4 w-4" />
              </span>
            </Link>
          </motion.div>
        </div>

        {/* Stats strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.85, duration: 0.6 }}
          className="mt-12 flex gap-8 border-t border-white/[0.06] pt-8"
        >
          {[
            { value: "2", label: "AI Modules" },
            { value: "RAG", label: "Architecture" },
            { value: "∞", label: "Queries / session" },
          ].map((s) => (
            <div key={s.label} className="flex flex-col gap-1">
              <span className="font-mono text-2xl font-extrabold text-emerald-400">{s.value}</span>
              <span className="font-mono text-[11px] uppercase tracking-widest text-slate-700">{s.label}</span>
            </div>
          ))}
        </motion.div>
      </div>
    </main>
  );
}