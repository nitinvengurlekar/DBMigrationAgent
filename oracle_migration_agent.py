# oracle_migration_agent.py

import streamlit as st
from jinja2 import Template
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import os

openai_api_key = st.secrets['openai']["OPENAI_API_KEY"]
st.title("Oracle Cloud DB Migration Agent")
st.markdown("Provide inputs to generate a migration guide and SOW document.")

with st.form("migration_form"):
    db_size = st.text_input("Database Size", "2TB")
    downtime = st.text_input("Downtime Window", "5 hours")
    upgrade_required = st.selectbox("Is Upgrade Required?", ["Yes", "No"])
    current_version = st.text_input("Current DB Version", "12.2")
    target_version = st.text_input("Target DB Version", "19c")
    platform = st.text_input("Target Platform", "Exadata Cloud Service")
    nonprod = st.selectbox("Include Non-Prod Environments?", ["Yes", "No"])
    submitted = st.form_submit_button("Generate Migration Guide and SOW")

# Initialize the LLM once, outside of function
llm = ChatOpenAI(
    model_name="gpt-4o",
    temperature=0.2
)

if submitted:
    user_input = {
        "database_size": db_size,
        "downtime_window": downtime,
        "upgrade_required": upgrade_required == "Yes",
        "current_version": current_version,
        "target_version": target_version,
        "target_platform": platform,
        "include_nonprod": nonprod == "Yes"
    }

    def generate_migration_guide(input_dict):
        prompt = f"""
        Create a 3-part Oracle DB migration guide:
        1. Planning
        2. Execution
        3. Post-Migration Validation

        Use the following inputs:
        - DB size: {input_dict['database_size']}
        - Downtime: {input_dict['downtime_window']}
        - Upgrade: {input_dict['upgrade_required']}
        - Version: {input_dict['current_version']} to {input_dict['target_version']}
        - Platform: {input_dict['target_platform']}
        - Non-Prod included: {input_dict['include_nonprod']}

        Each section should be thorough and professional.
        """
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            return f"Error generating migration guide: {e}"

    migration_guide = generate_migration_guide(user_input)

    st.subheader("Migration Guide")
    st.text_area("Generated Guide", migration_guide, height=300)

    sow_template = Template("""
Schedule A: Statement of Work
Project: Migration and Upgrade to Oracle Cloud
Client: [Client Name]
Effective Date: [TBD]

1. Objectives & Scope
Migrate the on-premise Oracle DB ({{ db_size }}, version {{ current_version }}) to {{ platform }} ({{ target_version }}) with a maximum offline window of {{ downtime }}.

2. High-Level Tasks & Estimates

| Phase                          | Description                                              | Effort (hrs) |
|--------------------------------|----------------------------------------------------------|--------------|
| Assessment & Discovery        | Kick-off, review exachk, finalize DBs                   | 30           |
| Environment Provisioning      | Setup compute/network/storage/IAM                       | 40           |
| Pre-Migration Validation      | Use CPAT & DB Advisor                                    | 40           |
| ZDM Test Migration            | UAT migration & upgrade validation                      | 80           |
| Cutover Planning              | Dry-run, rollback strategy                               | 40           |
| Production Migration & Upgrade| RMAN restore, upgrade, validation                       | 16           |
| Post-Migration Support        | Tuning, incident response, KT                           | 40           |
| Project Mgmt & Reporting      | Status calls, issue tracking, closure                   | 32           |
| **Total**                     |                                                          | **{{ total_effort }}** |

3. Deliverables:
- Migration plan & runbooks
- Upgraded database on {{ platform }}
- Knowledge transfer documentation
- Final project closure report
    """)

    total_hours = 30 + 40 + 40 + 80 + 40 + 16 + 40 + 32
    rendered_sow = sow_template.render(
        db_size=db_size,
        current_version=current_version,
        target_version=target_version,
        downtime=downtime,
        platform=platform,
        total_effort=total_hours
    )

    st.subheader("Statement of Work (SOW)")
    st.text_area("Generated SOW", rendered_sow, height=400)

    st.download_button("Download SOW as Text", data=rendered_sow, file_name="oracle_migration_sow.txt")
