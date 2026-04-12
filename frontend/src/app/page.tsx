"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

const FEATURES = [
  {
    icon: "🧠",
    title: "Plain-English Queries",
    desc: "Ask anything about your data in natural language. No SQL knowledge required.",
  },
  {
    icon: "🔍",
    title: "Full Transparency",
    desc: "Every answer shows the SQL it ran, confidence level, and a hallucination check.",
  },
  {
    icon: "🔒",
    title: "Privacy by Default",
    desc: "Sensitive columns are automatically hidden based on your role — no config needed.",
  },
  {
    icon: "📊",
    title: "Auto Visualisation",
    desc: "Charts, tables, and metric cards are chosen automatically to best fit your data.",
  },
  {
    icon: "⚡",
    title: "Anomaly Detection",
    desc: "Statistical outliers are flagged on every result so you never miss something unusual.",
  },
  {
    icon: "💬",
    title: "Multi-turn Memory",
    desc: "Follow-up questions understand full context — just like talking to an analyst.",
  },
];

export default function LandingPage() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-border/50 max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-purple/20 flex items-center justify-center text-purple font-bold text-lg">X</div>
          <span className="text-lg font-bold tracking-tight">InsightX AI</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/login")}
            className="text-sm text-text3 hover:text-text transition-colors px-4 py-1.5"
          >
            Sign in
          </button>
          <button
            onClick={() => router.push("/login?mode=signup")}
            className="text-sm bg-purple hover:bg-purple/90 text-white font-medium px-4 py-1.5 rounded-lg transition-colors"
          >
            Get started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 max-w-4xl mx-auto w-full animate-fade-up">
        <div className="inline-flex items-center gap-2 bg-purple/10 border border-purple/20 text-purple text-xs font-medium px-3 py-1 rounded-full mb-6">
          NatWest Group Hackathon · Talk to Data
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight mb-6">
          Ask your data{" "}
          <span className="text-purple">anything.</span>
          <br />Get honest answers.
        </h1>

        <p className="text-text2 text-lg max-w-xl mb-10 leading-relaxed">
          Upload a CSV or Excel file and start asking questions in plain English.
          InsightX generates SQL, runs it, explains the results — and shows its work.
        </p>

        <div className="flex items-center gap-4 flex-wrap justify-center">
          <button
            onClick={() => router.push("/login?mode=signup")}
            className="bg-purple hover:bg-purple/90 text-white font-semibold px-7 py-3 rounded-xl text-sm transition-colors"
          >
            Start for free →
          </button>
          <button
            onClick={() => router.push("/login")}
            className="bg-surface border border-border hover:border-purple/30 text-text2 hover:text-text font-medium px-7 py-3 rounded-xl text-sm transition-colors"
          >
            Sign in
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 pb-24 max-w-6xl mx-auto w-full">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-surface border border-border rounded-xl p-5 hover:border-purple/30 transition-colors"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-sm mb-1">{f.title}</h3>
              <p className="text-text3 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 px-6 py-5 text-center text-text3 text-xs">
        InsightX AI · Built for NatWest Group Hackathon
      </footer>
    </div>
  );
}
