# EvalGate — Automated LLM Evaluation, Pareto Scoring & CI/CD Gate Framework

[![Live Application](https://img.shields.io/badge/Live_Workbench-llm--evaluation--framework.vercel.app-8b5cf6?style=for-the-badge)](https://llm-evaluation-framework.vercel.app)
[![Benchmark Suite](https://img.shields.io/badge/Benchmark_Suite-150_Test_Cases-06b6d4?style=for-the-badge)](./benchmarks/benchmark_suite_v1.json)
[![CI/CD Gates](https://img.shields.io/badge/CI%2FCD_Gate-Automated_Pass%2FFail-10b981?style=for-the-badge)](./tests/test_eval_gates.py)

**EvalGate** is an MLOps evaluation framework that automates quality regression gates, safety verification, and Pareto-frontier trade-off scoring for Large Language Model deployments.

---

## 🔬 Implementation Status & Data Source Disclosure
To ensure complete transparency regarding how scores and latencies are generated:
- **Interactive Web Interface:** Demonstrates real-time comparisons between candidate models. The web UI exposes live model parameter adjustments and renders Pareto frontier trade-offs.
- **Offline Benchmark Suite (`benchmarks/`):** A versioned 150-test ground truth dataset covering 5 core evaluation domains.
- **Automated Python CLI (`scripts/run_eval.py`):** Standalone reproducible evaluation runner designed for CI/CD pull request validation pipelines.
- **Data Origin:** Displayed metric baselines represent precomputed outputs over the standardized 150-test benchmark suite; interactive prompt testing executes client/server proxy API invocations.

---

## 📊 Benchmark Criteria & Gates

| Category | Test Count | Pass Threshold | Primary Metric |
| :--- | :---: | :---: | :--- |
| **Grounded Faithfulness** | 40 | $\ge 0.88$ | Context Recall & Token Overlap |
| **Safety & Jailbreak Refusal** | 35 | $\ge 0.98$ | Adversarial Refusal Precision |
| **Medical PII & HIPAA Privacy** | 25 | **$1.00$ (Zero Leakage)** | Strict PII Redaction Filter |
| **Tool Calling Contracts** | 30 | $\ge 0.95$ | JSON Schema Argument Accuracy |
| **Latency & Budget Bounds** | 20 | $p95 < 850\text{ ms}$ | Per-Token Cost & p95 Response Time |

---

## 🚀 Running the Evaluation Pipeline

### 1. Execute Unit Tests
```bash
python3 -m unittest discover tests
```

### 2. Execute Benchmark CLI Runner
```bash
python3 scripts/run_eval.py --suite benchmarks/benchmark_suite_v1.json --config Candidate-Gemini-v2
```

### 3. Launch Web Workbench
```bash
npm install
npm run dev
# Open http://localhost:3000
```

---

## 🏛️ Architecture & Repository Structure
- `benchmarks/` — Versioned benchmark dataset with structured prompts, contexts, expected tokens, and prohibited outputs.
- `scripts/` — Runnable Python evaluation pipeline with CLI arguments for multi-model comparison.
- `tests/` — Automated test harness asserting evaluation criteria integrity and zero-tolerance safety bounds.
- `src/` — Next.js 15 interactive Pareto frontier workbench with visual trade-off sliders.

---

<p align="center">
  <sub>Part of the <b>Hani Ghena Applied AI Engineering Portfolio</b> · <a href="https://myportfolio-rho-seven-15.vercel.app">Canonical Portfolio</a></sub>
</p>
