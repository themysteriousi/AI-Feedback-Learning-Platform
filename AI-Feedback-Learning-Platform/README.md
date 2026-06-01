# 🤖 AI Feedback Learning Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-LLM-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-DPO%2FRLHF-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**A Self-Improving Generative AI System with Automated Feedback Loops, Model Evaluation, and Continuous Learning on AWS**

[Architecture](#-system-architecture) • [Features](#-key-features) • [Tech Stack](#-tech-stack) • [Modules](#-modules) • [Setup](#-getting-started) • [MLOps Pipeline](#-mlops-pipeline)

</div>

---

## 📌 Project Overview

Most AI applications are deployed as **static systems**. Once deployed, their performance gradually degrades due to changing user requirements, evolving data distributions, domain-specific knowledge gaps, and model drift.

This platform solves that by creating an **end-to-end feedback ecosystem** where user interactions become training signals that continuously optimize future model behavior — implementing a complete production-scale MLOps lifecycle at near-zero infrastructure cost.

---

## 🎯 Core Objectives

| # | Objective |
|---|---|
| 1 | Collect explicit (ratings) and implicit (behavioral) user feedback |
| 2 | Analyze AI performance using quantitative metrics |
| 3 | Identify low-quality responses automatically with PII-safe data handling |
| 4 | Create feedback loops for model optimization via DPO/RLHF |
| 5 | Enable continuous retraining pipelines on free GPU resources |
| 6 | Monitor model drift, response quality, and compute costs |
| 7 | Deploy improved model versions automatically via CI/CD |
| 8 | Provide real-time insights through Streamlit analytics dashboards |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                               │
│              (Streamlit Cloud / Vercel - Free Hosted)               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  AWS API GATEWAY (Free Tier)                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│               AWS LAMBDA - Inference Handler (Free Tier)             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│           AMAZON BEDROCK - Serverless LLM (Pay-per-token)            │
│                    Claude / Llama / Mistral                          │
└──────────────┬────────────────────────────────────────┬─────────────┘
               │ Response                               │ Feedback
               ▼                                        ▼
┌──────────────────────────┐             ┌──────────────────────────────┐
│   Response Delivery      │             │   DynamoDB Feedback Store     │
│   to User Interface      │             │   (Explicit + Implicit)       │
└──────────────────────────┘             └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │     DynamoDB Streams          │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │  AWS Lambda - Data Processor  │
                                         │  + PII Redaction (Presidio)   │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │    S3 Data Lake               │
                                         │  (Cleaned Feedback Data)      │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │  Google Colab (Free T4 GPU)   │
                                         │  DPO / RLHF Fine-Tuning       │
                                         │  Hugging Face `trl` library   │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │  Model Registry               │
                                         │  (Hugging Face Hub / S3)      │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │  GitHub Actions CI/CD         │
                                         │  Automated Deployment         │
                                         └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │  CloudWatch + AWS Budgets     │
                                         │  Monitoring & Cost Alarms     │
                                         └──────────────────────────────┘
```

---

## ✨ Key Features

- **🔄 Automated Feedback Loop** — User ratings and behavioral signals automatically trigger model improvement workflows
- **🔒 PII Redaction** — Open-source Microsoft Presidio-based scrubbing before any data hits the data lake
- **🧠 DPO / RLHF Fine-Tuning** — Converts rated interactions into preference datasets for modern alignment training
- **📊 Real-Time Dashboards** — Streamlit-powered analytics tracking satisfaction, latency, drift, and token costs
- **🚀 CI/CD Deployment** — GitHub Actions automates model registration and deployment on every retraining cycle
- **💰 Near-Zero Cost** — Full enterprise MLOps stack running on AWS Free Tier + Serverless pay-per-use services
- **🛡️ Hallucination Detection** — Automated scoring of AI responses for factual inconsistency
- **📉 Model Drift Monitoring** — CloudWatch metrics track degradation over time and trigger retraining alerts

---

## 🧩 Modules

### Module 1 — AI Interaction Engine
> Serverless conversational AI using Amazon Bedrock with context retention and multi-turn interactions.

**Services:** `Amazon Bedrock` · `AWS Lambda` · `API Gateway`

---

### Module 2 — Feedback Collection Engine
> Captures explicit (star ratings, like/dislike) and implicit (session duration, re-read frequency) feedback signals.

**Services:** `DynamoDB` · `DynamoDB Streams`

---

### Module 3 — Data Processing Pipeline
> Event-driven pipeline that cleans, redacts PII, and writes feedback to the S3 Data Lake.

**Services:** `AWS Lambda` · `Amazon S3` · `Microsoft Presidio` · `Scikit-Learn`

---

### Module 4 — Model Improvement Engine (DPO/RLHF)
> Aggregates feedback, constructs preference datasets, and fine-tunes open-source LLMs using Direct Preference Optimization.

**Tools:** `Google Colab` · `Hugging Face trl` · `S3` · `PyTorch`

---

### Module 5 — MLOps & Observability
> Automates CI/CD deployment and provides dashboards for model performance, satisfaction, latency, and cost.

**Tools:** `GitHub Actions` · `CloudWatch` · `AWS Budgets` · `Streamlit`

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Cloud Platform** | AWS (Lambda, Bedrock, DynamoDB, S3, API Gateway, CloudWatch, Budgets) |
| **Generative AI** | Amazon Bedrock (Claude / Llama / Mistral) |
| **ML / Fine-Tuning** | PyTorch, Hugging Face `trl`, Scikit-Learn, DPO, RLHF |
| **Data Pipeline** | DynamoDB Streams, AWS Lambda, S3 Data Lake |
| **PII & Privacy** | Microsoft Presidio (open-source) |
| **CI/CD & DevOps** | GitHub Actions, Docker |
| **Model Registry** | Hugging Face Hub, Amazon S3 |
| **Dashboards** | Streamlit Community Cloud |
| **Languages** | Python 3.11, SQL |

---

## 🔄 MLOps Pipeline

```
Collect Feedback → Redact PII → Store in S3 → Build Preference Dataset
       ↓
DPO Fine-Tuning (Colab) → Register Model → Auto-Deploy (GitHub Actions)
       ↓
Monitor with CloudWatch → Detect Drift → Trigger Next Retraining Cycle
```

---

## 🔒 Security Implementation

| Control | Implementation |
|---|---|
| Access Control | IAM Role-Based Access Control |
| Data at Rest | S3 Server-Side Encryption (SSE-S3) |
| Data in Transit | TLS/HTTPS enforced across all services |
| API Security | API Gateway Authorization + Lambda Authorizer |
| Audit Logging | AWS CloudTrail |
| Network Isolation | VPC with private subnets |
| Secret Management | AWS Secrets Manager |
| PII Protection | Microsoft Presidio redaction in pipeline |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- AWS Account (Free Tier)
- GitHub Account
- Google Colab Account (for fine-tuning)

### Installation

```bash
# Clone the repository
git clone https://github.com/themysteriousi/AI-Feedback-Learning-Platform.git
cd AI-Feedback-Learning-Platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

```bash
cp .env.example .env
# Fill in your AWS credentials and Bedrock model ID
```

### Project Structure

```
AI-Feedback-Learning-Platform/
├── src/
│   ├── api/                    # Lambda handlers & API Gateway config
│   ├── feedback/               # Feedback collection & DynamoDB models
│   ├── pipeline/               # Data processing & PII redaction
│   ├── training/               # DPO fine-tuning notebooks & scripts
│   ├── monitoring/             # CloudWatch metrics & drift detection
│   └── dashboard/              # Streamlit analytics dashboard
├── infrastructure/
│   ├── lambda/                 # Lambda deployment packages
│   └── iam/                    # IAM role policies
├── .github/
│   └── workflows/              # GitHub Actions CI/CD pipelines
├── notebooks/
│   └── dpo_finetuning.ipynb    # Google Colab DPO training notebook
├── tests/                      # Unit & integration tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📈 Expected Outcomes

- **20–40% improvement** in AI response quality through iterative DPO fine-tuning
- **Reduced model drift** via automated retraining triggered on feedback thresholds
- **Real-time cost visibility** with AWS Budgets and token-level tracking
- **~$0/month infrastructure cost** using AWS Free Tier + Serverless architecture

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ to demonstrate production-grade MLOps on a zero-budget constraint**

</div>
