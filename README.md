# DBMigrationAgent
This repository maintains the scripts to deploy and enable Oracle Database Migration SOW Agent
# Oracle Cloud DB Migration Agent

This Streamlit application helps solution architects and database administrators quickly generate a comprehensive Oracle Cloud Database Migration plan and Statement of Work (SOW). It uses **LangChain** and **OpenAI GPT-4** to automate planning based on user-specified migration criteria.

## 🧠 What It Does

- Accepts key user inputs such as:
  - Database size
  - Downtime window
  - Source and target Oracle DB versions
  - Upgrade requirements
  - Target Oracle Cloud platform
- Generates:
  - A 3-part **Migration Guide**: Planning, Execution, and Post-Migration Validation
  - A formatted **Statement of Work (SOW)** with detailed effort breakdown and deliverables

## 🛠️ Technologies Used

- [Streamlit](https://streamlit.io/)
- [LangChain](https://github.com/langchain-ai/langchain)
- [OpenAI GPT-4](https://openai.com/)
- [Jinja2](https://palletsprojects.com/p/jinja/)

## 🚀 Quick Start

### 1. Clone this Repository

```bash
git clone https://github.com/YOUR-USERNAME/oracle-migration-agent.git
cd oracle-migration-agent
