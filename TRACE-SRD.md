MalpracticeVibe: Unified Product & Systems Requirements Document (P-SRD)Target System: MalpracticeVibe Autonomous Workspace CoreDeployment Strategy: Single-Command Multi-Container Docker BuildSecurity Baseline: Air-Gapped Capable / HIPAA-Compliant Local File-System Context1. Product Vision & User JourneyMalpracticeVibe is a purpose-built workspace that handles everything from data collection to final demand drafting for medical malpractice legal teams. It replaces unorganized, multi-tool setups with a step-by-step pipeline. By wrapping open-source tools (Docspell, Orthanc, OHIF) inside structured open standards (Google OKF, Anthropic MCP, OMOP), it gives paralegals a simple 4-click workflow while keeping technical details under the hood.The 4-Click Paralegal User Journey┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│         CLICK 1         │     │         CLICK 2         │     │         CLICK 3         │     │         CLICK 4         │
│   Initialize Matter     │────>│   Drag-and-Drop Media   │────>│  Side-by-Side Validation │────>│    Download Demand      │
│  (Metriport Network &   │     │  (Automatic OCR/DICOM   │     │ (Interactive Timeline & │     │ (Automated Case Document│
│   Statute Calculation)  │     │   File System Routing)  │     │   OHIF Scan Stream)     │     │      Compilation)       │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
Click 1: Initialize Matter (Intake Phase)The User Experience: The paralegal opens the dashboard and types in core client data: Name, DOB, Address, Incident Date, Incident State, and a brief description. They click "Initialize Case Matter." The screen displays a success badge alongside an automated legal checklist showing the state's Statute of Limitations deadline.Behind-the-Scenes Tech Execution: The backend creates a unique case directory using the Google Open Knowledge Format (OKF) template structure. It instantly fires a secure webhook request containing the demographic variables out to the Metriport API to begin pulling records from the national HIE networks (Carequality/CommonWell).Click 2: Ingest Materials (Ingestion Phase)The User Experience: When a hospital sends physical files or a medical CD, the paralegal opens the "Ingest Materials" pane. They drag and drop all raw files, unorganized PDFs, and DICOM folders into a single upload zone. The system organizes the materials automatically.Behind-the-Scenes Tech Execution: An Anthropic Model Context Protocol (MCP) background server watches this directory. It inspects file headers. Raw imaging slices containing the DICM text signature are zipped and POSTed to Orthanc. Standard PDFs and images are routed to Docspell to run OCR. A background parser scans the text for provider names and adds missing clinics to the paralegal's request list.Click 3: Side-by-Side Validation (Review & Audit Phase)The User Experience: The paralegal clicks "Review Case File." The interface splits symmetrically down the center. The left side presents a zoomable, clickable, clean chronological timeline of the patient's medical history. The right side displays a dark-mode diagnostic imaging suite. Clicking a timeline event named "Lumbar MRI" instantly loads that specific scan on the right. Below the view, a red alert box highlights any billing mismatches.Behind-the-Scenes Tech Execution: Streamlit parses the client's OKF cache file (chronology.md). Clicking an entry reads its underlying file schema link. If it points to an orthanc:// address, a WebSocket message refreshes an embedded OHIF Viewer HTML5 iFrame to load that exact study frame. Simultaneously, a QuickUMLS script maps raw terminology to OMOP Common Data Model concepts, feeding a structured code matrix to a local LLM to flag clinical-to-billing gaps.Click 4: Generate Demand Package (Drafting Phase)The User Experience: The paralegal checks the boxes next to the confirmed anomalies and clicks "Build Demand Package." A browser file-save prompt appears, allowing them to download a fully populated, 15-page Microsoft Word document (.docx) containing a complete statement of facts, an itemized table of medical errors, and specific page-number citations.Behind-the-Scenes Tech Execution: The application executes DocxTemplate, loading a pre-vetted legal pleading file. It injects variables directly from the client's verified OKF file hierarchy. The generated .docx file is saved locally to the machine and logged back inside Docspell under a Demand Letter Generated file tag.2. Comprehensive System Architecture & Core Stack                                  ┌───────────────────────────┐
                                  │   Paralegal UI Web App    │
                                  │   (Streamlit Port 8501)   │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼ (JSON-RPC over StdIO)
                                  ┌───────────────────────────┐
                                  │   Anthropic MCP Server    │
                                  │ (System File Orchestration│
                                  └─────────────┬─────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼ (PDF / Paper Ingestion)                                     ▼ (DICOM Disc Slices Ingestion)
  ┌───────────────────────────────────────────┐                 ┌───────────────────────────────────────────┐
  │              Docspell Server              │                 │              Orthanc Server               │
  │         (OCR Engine - Port 7880)          │                 │         (DICOM Database - Port 8042)      │
  └──────────────┬────────────────────────────┘                 └──────────────┬────────────────────────────┘
                 │                                                             │
                 ▼ (Normalized Text Stream)                                    ▼ (WADO-RS Stream Access)
  ┌───────────────────────────────────────────┐                 ┌───────────────────────────────────────────┐
  │          QuickUMLS + OMOP Core            │                 │                OHIF Viewer                │
  │      (Medical Code Standardization)       │                 │         (HTML5 Frontend - Port 3000)      │
  └──────────────┬────────────────────────────┘                 └──────────────┬────────────────────────────┘
                 │                                                             │
                 └──────────────────────────────┬──────────────────────────────┘
                                                │
                                                ▼ (Deterministic Markdown Writing Loop)
                               ┌───────────────────────────────────┐
                               │  Google OKF Unified Case Cache   │
                               │  (Flat File System /storage/cases)│
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼ (Template Variable Injections)
                               ┌───────────────────────────────────┐
                               │           DocxTemplate            │
                               │   (Final Output Demand Assembly)  │
                               └───────────────────────────────────┘
Component Network Mapping & Port AllocationComponentRoleProtocolInternal Routing PortExternal Volume PathStreamlit CoreDashboard UI Web ApplicationHTTP8501:8501/workspace/appAnthropic MCPHost OS File / Script HandlerJSON-RPCStandard I/O/workspace/storageDocspell BackendUnstructured Document OCRREST API7880:7880/workspace/storage/docspell_uploadOrthanc DBCore DICOM Study StorageDICOM Web / REST8042:8042/workspace/storage/orthanc_uploadOHIF ViewerFront-end Radiology WorkstationWADO-RS Engine3000:3000Embedded UI EngineQuickUMLS / OMOPClinical Vocabulary NormalizerPython LibLocal ProcessShared memory cacheGoogle OKFDynamic Memory Storage LayerFlat DirectoryLocal IO/workspace/storage/casesDocxTemplateAutomated Document BuilderJinja2 PipelineLocal IO/workspace/app/templates3. Data Flow Diagrams (DFD)Level 0: Global System Context                        ┌────────────────────────────────────────────────────────┐
                        │                     Metriport HIE                      │
                        └───────┬────────────────────────────────────────▲───────┘
                                │                                        │
                                │ Patient JSON Docs                      │ Outbound Demographic Params
                                ▼                                        │
┌──────────────┐          ┌──────────────────────────────────────────────┴───────┐          ┌──────────────┐
│  Paralegal   │─────────>│                                                      │─────────>│ Output Legal │
│  Workstation │          │              MalpracticeVibe Core Engine             │          │ Documents    │
│  (UI Screen) │<─────────│                                                      │<─────────│ (.docx/.pdf) │
└──────────────┘          └──────────────────────────────────────────────────────┘          └──────────────┘
                                ▲                                        │
                                │                                        │
                                │ Raw DICOM Scan Files / Paper Scans     │ System Write Arrays
                                └────────────────────────────────────────▼
                        ┌────────────────────────────────────────────────────────┐
                        │                   Local Host Filesystem                │
                        └────────────────────────────────────────────────────────┘
Level 1: Deep-Dive Blueprint for the AI Coding Agent                          ┌───────────────────────────┐
                          │   Paralegal UI Action     │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Inputs Data Struct)
                          ┌───────────────────────────┐
                          │    Intake Module Event    │
                          └─────────────┬─────────────┘
                                        │
                ┌───────────────────────┴───────────────────────┐
                ▼                                               ▼
  ┌───────────────────────────┐                   ┌───────────────────────────┐
  │   Metriport API Launch    │                   │ Statute Lookup Validation │
  └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                │ (JSON Logs Payload)                           │ (State Code Match)
                └───────────────────────┬───────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │    Create OKF Directory   │
                          │   (/cases/[id]/index.md)  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │    MCP Server Drop Zone   │
                          └─────────────┬─────────────┘
                                        │
                ┌───────────────────────┴───────────────────────┐
                ▼ (DICM Header Match)                           ▼ (Non-DICOM / PDF Layout)
  ┌───────────────────────────┐                   ┌───────────────────────────┐
  │     Orthanc DB Storage    │                   │    Docspell Ingest Core   │
  │     (Study UID Mapping)   │                   │    (Background OCR Run)   │
  └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                │                                               │
                │ (Return Orthanc Reference)                    │ (Emit Raw Text Strings)
                └───────────────────────┬───────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │  QuickUMLS Term Matching  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Normalized Concept Matrix)
                          ┌───────────────────────────┐
                          │     OMOP Standardizer     │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Clean CPT / ICD Codes Table)
                          ┌───────────────────────────┐
                          │     Local LLM Auditor     │
                          │   (Evaluates rulebook.md) │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Output Inconsistency Logs)
                          ┌───────────────────────────┐
                          │   Generate Event MD Nodes │
                          │  (/events/billing_gap.md) │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   DocxTemplate Assembler  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼ (Jinja2 Pleading Variable Merge)
                          ┌───────────────────────────┐
                          │   Download Final Demand   │
                          └───────────────────────────┘
4. Google OKF Specifications & Storage SchemaThe AI agent must never store case files in an unorganized or ad-hoc format. Every case folder must be structured as a deterministic knowledge graph using the Google Open Knowledge Format (OKF). Cross-file references must use relative markdown links ([Label](relative_path.md)).text/workspace/storage/cases/[case_id]/
│
├── index.md                  # Master Case Graph Manifest Registry
├── chronology.md             # Timeflow-Formatted Chronological Timeline
│
└── events/                   # Folder housing atomic event file structures
    ├── 2026-07-01_er_intake_notes.md
    ├── 2026-07-02_spine_mri_scan.md
    └── 2026-07-03_billing_discrepancy.md
Use code with caution.Mandatory Markdown Templates for Coding Agent RealizationYour file-writing functions must output text following these exact structures:markdown# File Path: /workspace/storage/cases/[case_id]/index.md
# Master Case Index: [Unique Case Identifier Key]

## Case Metadata
- **Patient Legal Name**: Johnathan Smith
- **Date of Birth**: 1980-05-14
- **Date of Medical Incident**: 2026-01-15
- **Litigation Jurisdiction**: NY
- **Statute Evaluation Status**: CRITICAL_URGENT

## Core System Interop Links
- **Docspell Folder Identifier**: `http://localhost:7880/pool/default/folder/a98b-202c`
- **Orthanc Patient Reference UID**: `772154a-bc882190-ac`

## Active Structural Violations Discovered
- [Billing Inflation Discrepancy](events/2026-07-03_billing_discrepancy.md)
- [Unmapped Treatment Event](events/2026-07-01_er_intake_notes.md)
Use code with caution.markdown# File Path: /workspace/storage/cases/[case_id]/chronology.md
# Master Case Medical Chronology

- **2026-01-15 09:12:00**: Emergency Room Admittance for Acute Back Injury
  - *Data Origin Reference*: [Docspell Intake Document](docspell://item_id_7721)
  - *Context Node File*: [ER Intake Event Details](events/2026-07-01_er_intake_notes.md)

- **2026-01-15 13:00:00**: Radiology Scan Executed (Lumbar MRI)
  - *Data Origin Reference*: [Orthanc Diagnostic Scan File](orthanc://study_uid_9921)
  - *Context Node File*: [Spine MRI Analysis Context](events/2026-07-02_spine_mri_scan.md)

- **2026-01-17 11:30:00**: Final Itemized Facility Invoice Emitted
  - *Data Origin Reference*: [Docspell Ledger Item](docspell://item_id_8812)
  - *Context Node File*: [Billing Discrepancy Evaluation Log](events/2026-07-03_billing_discrepancy.md)
Use code with caution.markdown# File Path: /workspace/storage/cases/[case_id]/events/2026-07-03_billing_discrepancy.md
# Malpractice System Event: Billing Discrepancy Anomaly

## Document Baseline Mapping
- **System Event Execution Date**: 2026-07-03
- **Primary Source Document Instance**: [Facility Invoice #119A](docspell://item_id_8812)
- **Cross-Referenced Medical Record Link**: [ER Intake Event Details](2026-07-01_er_intake_notes.md)

## Standardized Medical Coding Vectors
- **Extracted Procedure Code (CPT)**: `99215` (High Complexity Outpatient Management, 40-54 Minutes)
- **Extracted Diagnostic Identifier (ICD-10)**: `M54.50` (Low Back Pain, Unspecified)
- **Unified OMOP Data Mapping Concept ID**: `443727` (Sensation of Pain in Back)

## Automated Audit Discrepancy Metrics
- **System Rule Violated Reference**: [Rule 04: Upcoding Medical Complexity](../../../rulebook.md#rule-04)
- **Factual Anomaly Findings**: Billed procedure CPT 99215 mandates at least 40 minutes of direct patient care. Cross-referenced physician progress notes show patient contact time was exactly '5 minutes'.
- **Paralegal Verification Status**: PENDING_REVIEW
Use code with caution.5. Instructions & Code Generation Targets for the AI AgentTo build this product correctly, your scripts must pass the following implementation checks.Target 1: The Code Extraction Engine (audit.py)Write a Python script that pulls raw text from Docspell, uses regex to extract billing codes, standardizes terms via OMOP mappings, and passes the structured data to a local LLM to flag gaps based on your rulebook.pythonimport re
import requests
import json
import os

def run_malpractice_audit(case_id, docspell_item_id):
    # 1. Fetch raw extracted text from Docspell API
    docspell_url = f"http://docspell:7880/api/v1/item/{docspell_item_id}/text"
    headers = {"Authorization": f"Bearer {os.getenv('DOCSPELL_API_KEY')}"}
    
    try:
        response = requests.get(docspell_url, headers=headers)
        raw_text = response.json().get("text", "")
    except Exception as e:
        return {"status": "ERROR", "message": f"Docspell connection failure: {str(e)}"}

    # 2. Execute Regex Extraction for Billing Metadata
    cpt_codes = re.findall(r'\b\d{5}\b', raw_text) # Isolates standard 5-digit CPT procedure codes
    icd10_codes = re.findall(r'\b[A-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?\b', raw_text) # Matches ICD-10 diagnostic blocks

    # 3. Simulate OMOP Mapping Standardization 
    # In a full deployment, this queries a local QuickUMLS / OMOP Sqlite instance
    omop_concept_matrix = []
    for code in icd10_codes:
        if "M54.5" in code:
            omop_concept_matrix.append({"code": code, "omop_id": 443727, "standard_term": "Low Back Pain"})

    # 4. Load System Malpractice Rules
    with open('/workspace/app/rulebook.md', 'r') as f:
        audit_rulebook = f.read()

    # 5. Pack Context Payload and Send to Secure Local LLM Endpoint
    ollama_payload = {
        "model": "llama3",
        "prompt": f"""
        Analyze this patient's medical records for upcoding, discrepancies, and provider malpractice.
        
        SYSTEM MAPPED CODES:
        CPT Procedure Codes Detected: {cpt_codes}
        ICD-10 Diagnostic Codes Detected: {icd10_codes}
        OMOP Unified Terminologies: {omop_concept_matrix}
        
        RAW EXTRACTED CLINICAL TEXT:
        \"\"\"{raw_text}\"\"\"
        
        FIRM AUDIT RULEBOOK GUIDELINES:
        \"\"\"{audit_rulebook}\"\"\"
        
        Generate a valid Google OKF event file layout tracking any uncovered inconsistencies. Use the formatting shown in the specification docs.
        """,
        "stream": False
    }
    
    # 6. Write the Output to the OKF Directory
    llm_response = requests.post("http://localhost:11434/api/generate", json=ollama_payload)
    generated_markdown = llm_response.json().get("response", "")
    
    output_path = f"/workspace/storage/cases/{case_id}/events/detected_billing_gap.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(generated_markdown)
        
    return {"status": "SUCCESS", "target_written": output_path}
Use code with caution.Target 2: The Core Workspace View (main.py)Write a Streamlit frontend script that splits the screen into a layout showing the interactive chronological timeline on the left and the embedded OHIF viewer frame on the right.pythonimport streamlit as st
import os

st.set_page_config(layout="wide")
st.title("MalpracticeVibe Workspace Engine")

# Active Case Session Tracking State Initialization
if "selected_case" not in st.session_state:
    st.session_state.selected_case = "case_101"
if "active_imaging_uid" not in st.session_state:
    st.session_state.active_imaging_uid = "default_study_placeholder"

# Initialize Symmetric Dynamic Workstation Columns
col_left_timeline, col_right_radiology = st.columns(2)

with col_left_timeline:
    st.header("Patient Chronological History (OKF Format)")
    
    # Read the OKF chronology file directly from local storage
    chronology_file_path = f"/workspace/storage/cases/{st.session_state.selected_case}/chronology.md"
    
    if os.path.exists(chronology_file_path):
        with open(chronology_file_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            if line.startswith("- **"):
                # Render the timeline event
                st.markdown(line)
                
                # Vibe Coding Logic: If line points to an Orthanc scan, create a viewing action button
                if "orthanc://" in line:
                    # Extract the Study UID from the link string configuration
                    extracted_uid = line.split("orthanc://study_uid_")[1].split(")")[0].strip()
                    if st.button(f"Stream Image Studies for Event Asset: {extracted_uid}", key=extracted_uid):
                        st.session_state.active_imaging_uid = extracted_uid
    else:
        st.info("No active chronology file detected for this matter profile. Run Ingestion pipeline.")

with col_right_radiology:
    st.header("Radiology Diagnostic Suite (OHIF Engine)")
    
    # Rebuild the iframe path to target the active imaging token state variable
    ohif_iframe_target_url = f"http://localhost:3000/viewer?StudyInstanceUIDs={st.session_state.active_imaging_uid}"
    
    # Inject the HTML5 interactive iFrame layout safely into the panel interface
    st.components.v1.iframe(src=ohif_iframe_target_url, height=700, scrolling=True)
Use code with caution.6. Engineering Requirements & Implementation RulesWhen implementing this system, ensure your scripts adhere to these strict programming invariants:Deterministic Content Access via MCP: The file routing system must use direct paths under /workspace/storage/. It should never fall back to heuristic file matching or fuzzy name parsing when writing to the OKF directories.No Context Leakage / Strict Data Boundaries: The local AI processing layer must look up validation conditions exclusively within the provided local rulebook.md. It must never mix medical assessment concepts across different client case folders.Flat Data Independence: The application must never store metadata inside a hidden or proprietary database format. If the Streamlit application container goes down, every file inside the OKF directory (/storage/cases/) must remain a standard, raw markdown file that can be opened and read by any human text editor.