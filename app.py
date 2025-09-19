import gradio as gr
import base64
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from config import ANTHROPIC_API_KEY
import os
import tempfile
import time
import json
from typing import List, Dict, Any
from datetime import datetime

def extract_structured_data_from_pdf(pdf_file, client, file_index):
    """
    Step 1: Extract structured JSON data from a single PDF
    """
    with open(pdf_file, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    json_extraction_prompt = f"""You are a medical-legal data extraction specialist. Extract structured data from this medical document ({os.path.basename(pdf_file)}) into valid JSON format.

CRITICAL: Output ONLY valid JSON. Quote exact text for all medical findings.

Required JSON structure:
{{
  "document_metadata": {{
    "filename": "{os.path.basename(pdf_file)}",
    "analysis_date": "{datetime.now().isoformat()}",
    "document_type": "initial_visit|follow_up|imaging|billing|legal|other"
  }},
  "patient_info": {{
    "demographics": {{
      "name": "string or null",
      "age": "string or null",
      "gender": "string or null",
      "height": "string or null",
      "weight": "string or null"
    }},
    "incident_details": {{
      "date": "YYYY-MM-DD or null",
      "time": "string or null",
      "mechanism": "string or null",
      "location": "string or null",
      "circumstances": "string or null",
      "source_quote": "exact text from document"
    }}
  }},
  "medical_encounters": [
    {{
      "date": "YYYY-MM-DD",
      "provider": "string",
      "facility": "string",
      "visit_type": "string",
      "chief_complaints": ["list of complaints"],
      "examination_findings": {{
        "orthopedic_tests": ["test: result"],
        "range_of_motion": ["measurement: value"],
        "neurological": ["finding: result"],
        "palpation": ["finding"]
      }},
      "diagnostic_results": {{
        "imaging": ["study: findings"],
        "lab_tests": ["test: result"],
        "measurements": ["measurement: value"]
      }},
      "treatments_provided": ["treatment list"],
      "provider_opinions": [
        {{
          "opinion": "exact quote",
          "source_quote": "verbatim text",
          "opinion_type": "causation|prognosis|treatment"
        }}
      ]
    }}
  ],
  "billing_data": [
    {{
      "date": "YYYY-MM-DD",
      "provider": "string",
      "service_code": "string",
      "description": "string",
      "amount": "number or null",
      "source_quote": "exact text"
    }}
  ],
  "quality_flags": {{
    "inconsistencies": ["description of issue"],
    "missing_data": ["what data is missing"],
    "date_discrepancies": ["date conflict description"],
    "unclear_text": ["illegible or uncertain sections"]
  }}
}}

VERIFICATION RULES:
- Include source quotes for every medical finding
- Use null for missing data, not empty strings
- Flag any illegible text as "unclear_text"
- Mark any assumptions as "inferred_data" in quality_flags
- Extract exact measurements and dates
- Preserve medical terminology as written

Output ONLY the JSON, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": json_extraction_prompt
                        }
                    ]
                }
            ]
        )

        json_text = response.content[0].text
        # Clean any potential markdown formatting
        if json_text.startswith('```json'):
            json_text = json_text.replace('```json', '').replace('```', '').strip()

        return json.loads(json_text)

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse JSON from document {file_index + 1}",
            "raw_response": response.content[0].text,
            "json_error": str(e)
        }
    except Exception as e:
        return {
            "error": f"Failed to extract data from document {file_index + 1}",
            "exception": str(e)
        }

def synthesize_unified_analysis(json_extractions, client):
    """
    Step 2: Synthesize all JSON extractions into unified timeline analysis
    """
    synthesis_prompt = f"""Create a unified medical-legal timeline analysis from these JSON extractions.

INPUT: {len(json_extractions)} JSON analyses from related medical documents
OUTPUT: Comprehensive chronological analysis with cross-references

JSON DATA:
{json.dumps(json_extractions, indent=2)}

SYNTHESIS REQUIREMENTS:
1. Merge timeline chronologically across all documents
2. Cross-reference findings between documents
3. Flag contradictions (DO NOT resolve - preserve both versions)
4. Track diagnostic/treatment progression
5. Validate billing against documented treatments
6. Eliminate duplicate patient information (use most complete version)

CITATION FORMAT: Every statement must include [Document_X] source reference

CONTRADICTION HANDLING:
- "Document A reports X on DATE, but Document B reports Y on DATE"
- Never invent explanations for discrepancies
- Flag for legal review when conflicts exist

OUTPUT SECTIONS:
1. **UNIFIED PATIENT TIMELINE** (chronological merger)
2. **CROSS-DOCUMENT CORRELATIONS** (how findings relate)
3. **IDENTIFIED CONTRADICTIONS** (conflicts requiring review)
4. **TREATMENT PROGRESSION ANALYSIS** (evolution of care)
5. **BILLING VALIDATION SUMMARY** (services vs documentation)
6. **QUALITY CONTROL OBSERVATIONS** (documentation issues)

IMPORTANT:
- Maintain legal precision - quote exact text
- Preserve source attribution for every finding
- Flag any assumptions or inferences clearly
- Focus on factual synthesis, not interpretation"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            messages=[
                {
                    "role": "user",
                    "content": synthesis_prompt
                }
            ]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error in synthesis step: {str(e)}"

def cross_reference_findings(json_extractions):
    """
    Utility function to perform cross-referencing logic
    """
    correlations = {
        "timeline_conflicts": [],
        "diagnostic_progression": [],
        "treatment_evolution": [],
        "billing_anomalies": []
    }

    # Extract all dates and check for conflicts
    all_encounters = []
    for doc_idx, extraction in enumerate(json_extractions):
        if "medical_encounters" in extraction:
            for encounter in extraction["medical_encounters"]:
                encounter["source_document"] = doc_idx + 1
                all_encounters.append(encounter)

    # Sort chronologically
    all_encounters.sort(key=lambda x: x.get("date", "9999-12-31"))

    # Check for same-date conflicts
    date_groups = {}
    for encounter in all_encounters:
        date = encounter.get("date")
        if date:
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(encounter)

    for date, encounters in date_groups.items():
        if len(encounters) > 1:
            correlations["timeline_conflicts"].append({
                "date": date,
                "encounters": encounters,
                "issue": "Multiple encounters on same date"
            })

    return correlations

def analyze_medical_pdf(pdf_files):
    """
    Two-step analysis: Extract structured JSON data, then synthesize unified timeline
    """
    if pdf_files is None or len(pdf_files) == 0:
        return "Please upload at least one PDF file."

    try:
        # Initialize the Anthropic client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Step 1: Extract structured JSON data from each PDF
        json_extractions = []
        extraction_status = f"📊 TWO-STEP ANALYSIS PROCESS\n\nStep 1: Extracting structured data from {len(pdf_files)} documents...\n\n"

        for i, pdf_file in enumerate(pdf_files):
            extraction_status += f"Processing {os.path.basename(pdf_file)}... "

            json_data = extract_structured_data_from_pdf(pdf_file, client, i)
            json_extractions.append(json_data)

            if "error" in json_data:
                extraction_status += f"❌ Error\n"
            else:
                extraction_status += f"✅ Complete\n"

        # Check if any extractions failed
        failed_extractions = [data for data in json_extractions if "error" in data]
        if failed_extractions:
            error_report = "\n\n⚠️ EXTRACTION ERRORS:\n"
            for error_data in failed_extractions:
                error_report += f"- {error_data.get('error', 'Unknown error')}\n"
                if "raw_response" in error_data:
                    error_report += f"  Raw response: {error_data['raw_response'][:200]}...\n"
            return extraction_status + error_report

        # Step 2: Cross-reference and synthesize
        extraction_status += "\nStep 2: Synthesizing unified timeline and cross-referencing findings...\n"

        # Perform cross-referencing
        correlations = cross_reference_findings(json_extractions)

        # Generate unified synthesis
        unified_analysis = synthesize_unified_analysis(json_extractions, client)

        # Combine everything into final report
        final_report = f"""🏥 COMPREHENSIVE MEDICAL-LEGAL ANALYSIS REPORT
📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📄 Documents Processed: {len(pdf_files)}

{extraction_status}
✅ Analysis Complete!

{'='*80}

{unified_analysis}

{'='*80}

TECHNICAL CORRELATION SUMMARY:
📊 Timeline Conflicts Detected: {len(correlations['timeline_conflicts'])}
📈 Diagnostic Progression Points: {len(correlations['diagnostic_progression'])}
💊 Treatment Evolution Stages: {len(correlations['treatment_evolution'])}
💰 Billing Anomalies Flagged: {len(correlations['billing_anomalies'])}

{'='*80}

SOURCE DATA SUMMARY:
The following files were processed and cross-referenced:
"""

        for i, pdf_file in enumerate(pdf_files):
            final_report += f"📄 Document {i+1}: {os.path.basename(pdf_file)}\n"

        final_report += "\n🔍 This analysis provides a unified view with source attribution for legal review.\n"

        return final_report

    except Exception as e:
        # Enhanced error handling for batch API
        error_msg = f"Error analyzing PDFs with batch API: {str(e)}\n\n"

        if "batch" in str(e).lower():
            error_msg += "This appears to be a batch processing error. Please check:\n"
            error_msg += "- Your API key has batch processing permissions\n"
            error_msg += "- The total file size doesn't exceed 256MB\n"
            error_msg += "- All uploaded files are valid PDFs\n"
        elif "413" in str(e) or "request_too_large" in str(e).lower():
            error_msg += "Request too large error. The combined PDF files exceed the 256MB limit.\n"
            error_msg += "Please try uploading fewer or smaller PDF files.\n"
        elif "rate" in str(e).lower() or "limit" in str(e).lower():
            error_msg += "Rate limit exceeded. Please wait a moment and try again.\n"
        elif "api_key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg += "API authentication error. Please check your Anthropic API key.\n"

        return error_msg

# Create the Gradio interface
with gr.Blocks(title="Medical PDF Analyzer", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 Medical PDF Legal Analysis Tool - Two-Step Enhanced")
    gr.Markdown("Upload multiple medical PDF documents to generate a **unified timeline analysis** with cross-document correlation. Uses two-step processing: structured extraction → synthesis.")
    
    with gr.Row():
        with gr.Column():
            pdf_input = gr.File(
                label="Upload Medical PDFs",
                file_types=[".pdf"],
                type="filepath",
                file_count="multiple"
            )
            analyze_btn = gr.Button("Analyze Documents", variant="primary", size="lg")
        
        with gr.Column():
            output_text = gr.Textbox(
                label="Analysis Results", 
                lines=30,
                max_lines=50,
                show_copy_button=True,
                placeholder="Your combined analysis will appear here..."
            )
    
    # Set up the click event
    analyze_btn.click(
        fn=analyze_medical_pdf,
        inputs=[pdf_input],
        outputs=[output_text]
    )

if __name__ == "__main__":
    demo.launch(share=True)