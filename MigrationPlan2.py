import streamlit as st
from jinja2 import Template
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
import requests
from bs4 import BeautifulSoup

os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']

st.title("Oracle Cloud DB Migration Agent")
st.markdown("Provide inputs to generate a migration guide and SOW document. This agent also references Oracle's official migration planning guide.")

# Helper to fetch and summarize migration guide content from Oracle's site
@st.cache_data(show_spinner=False)
def fetch_migration_guide_content(base_url):
    try:
        guide_text = []
        # Fetch main page
        resp = requests.get(base_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Collect main page paragraphs
        for p in soup.select('article p'):
            guide_text.append(p.get_text(strip=True))
        # Find and follow sublinks under the migration guide section
        sublinks = set()
        for a in soup.select('article a[href]'):
            href = a['href']
            if href.startswith('/'):
                href = 'https://www.oracle.com' + href
            if base_url in href or 'oracle.com/database/cloud-migration/' in href:
                sublinks.add(href)
        # Fetch each sublink and extract text
        for link in sublinks:
            try:
                r = requests.get(link)
                r.raise_for_status()
                sub_soup = BeautifulSoup(r.text, 'html.parser')
                for p in sub_soup.select('article p'):
                    guide_text.append(p.get_text(strip=True))
            except Exception:
                continue
        return '\n'.join(guide_text[:1000])  # limit to first 1000 lines for brevity
    except Exception as e:
        return f"Could not fetch guide content: {e}"

with st.form("migration_form"):
    db_size = st.text_input("Database Size", "2TB")
    downtime = st.text_input("Downtime Window", "5 hours")
    upgrade_required = st.selectbox("Is Upgrade Required?", ["Yes", "No"])
    current_version = st.text_input("Current DB Version", "12.2")
    target_version = st.text_input("Target DB Version", "19c")
    platform = st.text_input("Target Platform", "Exadata Cloud Service")
    nonprod = st.selectbox("Include Non-Prod Environments?", ["Yes", "No"])
    submitted = st.form_submit_button("Generate Migration Guide and SOW")

# Initialize the LLM once
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
    oracle_guide_url = "https://www.oracle.com/database/cloud-migration/"
    oracle_guide_content = fetch_migration_guide_content(oracle_guide_url)

    def generate_migration_guide(input_dict, guide_text):
        prompt = f"""
        You are an expert Oracle Cloud migration consultant.  You have access to Oracle's official migration planning guide:
        {guide_text}

        Using this as reference, create a 3-part Oracle DB migration guide:
        1. Planning
        2. Execution
        3. Post-Migration Validation

        Include insights drawn from the Oracle guide content and walk through key subtopics and best practices.

        Use the following inputs:
        - DB size: {input_dict['database_size']}
        - Downtime: {input_dict['downtime_window']}
        - Upgrade required: {input_dict['upgrade_required']}
        - Current version: {input_dict['current_version']}
        - Target version: {input_dict['target_version']}
        - Target platform: {input_dict['target_platform']}
        - Include non-prod: {input_dict['include_nonprod']}

        Provide a thorough, professional guide.
        """
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            return f"Error generating migration guide: {e}"

    migration_guide = generate_migration_guide(user_input, oracle_guide_content)

    st.subheader("Migration Guide")
    st.text_area("Generated Guide", migration_guide, height=300)

    # Statement of Work
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
