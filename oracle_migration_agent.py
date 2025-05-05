import streamlit as st
from jinja2 import Template
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
import requests
from bs4 import BeautifulSoup
import pdfplumber
import re

os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']

st.title("Oracle Cloud DB Migration Agent")
st.markdown("Provide inputs to generate a migration guide and SOW document. This agent references Oracle's official migration planning guide and an optional PDF reference for the SOW, including section-specific extraction.")

# PDF section extraction helper
@st.cache_data(show_spinner=False)
def extract_pdf_sections(uploaded_pdf, section_titles):
    try:
        text_all = ""
        tables_text = []
        with pdfplumber.open(uploaded_pdf) as pdf:
            # Extract full text
            pages = [page.extract_text() or '' for page in pdf.pages]
            text_all = '\n'.join(pages)
            # Extract tables on all pages
            for page in pdf.pages:
                for table in page.extract_tables():
                    header = table[0]
                    rows = table[1:]
                    table_str = ' | '.join(header) + '\n'
                    table_str += '\n'.join([' | '.join([cell or '' for cell in row]) for row in rows])
                    tables_text.append(table_str)
        # Find sections by headings
        sections = {}
        for title in section_titles:
            pattern = rf"{title}\s*(.*?)(?=\n[A-Z][a-z]+:|$)"
            match = re.search(pattern, text_all, re.DOTALL | re.IGNORECASE)
            if match:
                sections[title] = match.group(1).strip()
        # Combine extracted sections and tables
        combined = []
        for title in section_titles:
            if title in sections:
                combined.append(f"{title}:\n{sections[title]}")
        if tables_text:
            combined.append("-- Extracted Tables --")
            combined.extend(tables_text)
        return '\n\n'.join(combined)
    except Exception as e:
        return f"Could not extract PDF sections: {e}"

# Fetch Oracle online migration guide content
@st.cache_data(show_spinner=False)
def fetch_migration_guide_content(base_url):
    try:
        guide_text = []
        resp = requests.get(base_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for p in soup.select('article p'):
            guide_text.append(p.get_text(strip=True))
        sublinks = set()
        for a in soup.select('article a[href]'):
            href = a['href']
            if href.startswith('/'):
                href = 'https://www.oracle.com' + href
            if base_url in href or 'oracle.com/database/cloud-migration/' in href:
                sublinks.add(href)
        for link in sublinks:
            try:
                r = requests.get(link)
                r.raise_for_status()
                sub_soup = BeautifulSoup(r.text, 'html.parser')
                for p in sub_soup.select('article p'):
                    guide_text.append(p.get_text(strip=True))
            except Exception:
                continue
        return '\n'.join(guide_text[:1000])
    except Exception as e:
        return f"Could not fetch guide content: {e}"

# Upload optional PDF for SOW reference
doc_pdf = st.file_uploader("Upload reference PDF for SOW (optional)", type=["pdf"])
pdf_excerpt = None
if doc_pdf:
    # Specify sections to extract
    sections = ["Introduction", "Objective", "Scope and Task Plan", "Assumptions"]
    pdf_excerpt = extract_pdf_sections(doc_pdf, sections)

with st.form("migration_form"):
    db_size = st.text_input("Database Size", "2TB")
    downtime = st.text_input("Downtime Window", "5 hours")
    upgrade_required = st.selectbox("Is Upgrade Required?", ["Yes", "No"])
    current_version = st.text_input("Current DB Version", "12.2")
    target_version = st.text_input("Target DB Version", "19c")
    platform = st.text_input("Target Platform", "Exadata Cloud Service")
    nonprod = st.selectbox("Include Non-Prod Environments?", ["Yes", "No"])
    submitted = st.form_submit_button("Generate Migration Guide and SOW")

# Initialize LLM
llm = ChatOpenAI(model_name="gpt-4o", temperature=0.2)

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

    # Generate Migration Guide
def generate_migration_guide(input_dict, guide_text, pdf_text=None):
    prompt_parts = [
        "You are an expert Oracle Cloud migration consultant.",
        "Oracle official migration planning guide content:",
        guide_text
    ]
    if pdf_text:
        prompt_parts.extend(["Reference PDF excerpt:", pdf_text])
    prompt_parts.append(
        "Create a 3-part Oracle DB migration guide: 1. Planning 2. Execution 3. Post-Migration Validation."
        f" Use inputs: DB size={input_dict['database_size']}, Downtime={input_dict['downtime_window']}"
        f", Upgrade={input_dict['upgrade_required']}, Versions={input_dict['current_version']} to"
        f" {input_dict['target_version']}, Platform={input_dict['target_platform']},"
        f" Include non-prod={input_dict['include_nonprod']}. Provide a thorough, professional guide."
    )
    prompt = "\n\n".join(prompt_parts)
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Error generating migration guide: {e}"

    migration_guide = generate_migration_guide(user_input, oracle_guide_content, pdf_excerpt)
    st.subheader("Migration Guide")
    st.text_area("Generated Guide", migration_guide, height=300)
    # Download button for Migration Guide
    st.download_button("Download Migration Guide as Text", data=migration_guide, file_name="oracle_migration_guide.txt")

    # Build SOW
template_str = """
Schedule A: Statement of Work
Project: Migration and Upgrade to Oracle Cloud
Client: [Client Name]
Effective Date: [TBD]

1. Objectives & Scope
Migrate the on-premise Oracle DB ({{ db_size }}, version {{ current_version }}) to {{ platform }} ({{ target_version }}) with a maximum offline window of {{ downtime }}.

2. High-Level Tasks & Estimates

| Phase                          | Description                                              | Effort (hrs) |
|--------------------------------|----------------------------------------------------------|--------------|
| Assessment & Discovery         |  Kick-off, review exachk, finalize DBs                   | 30           |
| Environment Provisioning       |  Setup compute/network/storage/IAM                       | 40           |
| Pre-Migration Validation       |  Use CPAT & DB Advisor                                   | 40           |
| ZDM Test Migration             |  UAT migration & upgrade validation                      | 80           |
| Cutover Planning               |  Dry-run, rollback strategy                              | 40           |
| Production Migration & Upgrade |  RMAN restore, upgrade, validation                       | 16           |
| Post-Migration Support         |  Tuning, incident response, KT                           | 40           |
| Project Mgmt & Reporting       |  Status calls, issue tracking, closure                   | 32           |
| **Total**                      |                                                          | **{{ total_effort }}** |

3. Deliverables:
- Migration plan & runbooks
- Upgraded database on {{ platform }}
- Knowledge transfer documentation
- Final project closure report
{{ pdf_section }}
"""
    pdf_section = ""
    if pdf_excerpt:
        pdf_section = "4. Reference Document Excerpt:\n" + pdf_excerpt.replace("\n", "\n> ")

    sow_template = Template(template_str)
    total_hours = 30 + 40 + 40 + 80 + 40 + 16 + 40 + 32
    rendered_sow = sow_template.render(
        db_size=db_size,
        current_version=current_version,
        target_version=target_version,
        downtime=downtime,
        platform=platform,
        total_effort=total_hours,
        pdf_section=pdf_section
    )
    st.subheader("Statement of Work (SOW)")
    st.text_area("Generated SOW", rendered_sow, height=400)

    # Download button for SOW
    st.download_button("Download SOW as Text", data=rendered_sow, file_name="oracle_migration_sow.txt")
