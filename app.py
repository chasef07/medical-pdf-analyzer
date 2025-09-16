import gradio as gr
import base64
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from config import ANTHROPIC_API_KEY
import os
import tempfile
import time
from typing import List

def analyze_medical_pdf(pdf_files):
    """
    Analyze multiple medical PDFs using Claude's Messages Batch API and return combined analysis results
    """
    if pdf_files is None or len(pdf_files) == 0:
        return "Please upload at least one PDF file."
    
    try:
        # Initialize the Anthropic client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Prepare batch requests for all PDF files
        batch_requests = []

        for i, pdf_file in enumerate(pdf_files):
            # Read the PDF file and encode to base64
            with open(pdf_file, "rb") as f:
                pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Create batch request for this PDF
            batch_requests.append(
                Request(
                    custom_id=f"medical-pdf-{i+1}",
                    params=MessageCreateParamsNonStreaming(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2048,
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
                                        "text": f"""You are a specialized medical-legal document reviewer. Analyze the provided medical chart PDF ({os.path.basename(pdf_file)}) and generate a comprehensive legal summary following the exact format and analytical depth demonstrated in professional medical record reviews.

EXTRACTION REQUIREMENTS

1. INCIDENT DOCUMENTATION
- Extract ALL accident/incident details: date, time, mechanism of injury, location
- Identify any date discrepancies between reports
- Note damage estimates, emergency services involvement, airbag deployment
- Flag conflicting accounts of how incident occurred
- Extract witness statements or police report references

2. CHRONOLOGICAL TIMELINE CONSTRUCTION
- Organize all medical encounters in strict chronological order
- Include: Date, Provider, Facility, Visit type (initial, follow-up, diagnostic)
- Note treatment gaps or delays in care
- Identify progression from conservative to invasive treatments

3. CLINICAL DATA EXTRACTION

Initial Presentations:
- Chief complaints and symptom onset timing
- Pain levels, locations, and characteristics
- Functional limitations and ADL impacts
- Sleep disturbances and work impact

Physical Examination Findings:
- Orthopedic tests (positive/negative with specific test names)
- Range of motion limitations (quantify percentages)
- Palpable muscle spasms, trigger points
- Neurological findings (strength testing, reflexes, sensation)
- Any missing standard assessments

Diagnostic Studies:
- X-ray findings: alignment, degenerative changes, curve abnormalities
- MRI results: disc herniations (size, location, spinal cord contact)
- NCV/EMG results: nerve compressions, radiculopathies
- Any other imaging or diagnostic tests

4. TREATMENT DOCUMENTATION
- List all treatment modalities provided
- Frequency and duration of treatment plans
- Patient response to treatments (improvement/plateau/worsening)
- Treatment modifications and rationale
- Referrals to specialists with timing

5. DIAGNOSTIC PROGRESSION
- Initial diagnoses vs. evolving diagnoses
- Addition of new conditions (e.g., radiculopathy onset)
- ICD-10 codes where available
- Relationship between objective findings and diagnoses

6. CAUSATION ANALYSIS
- Medical opinions linking injuries to incident
- "Reasonable degree of medical certainty" statements
- Provider qualifications making causation statements
- Timing of causation opinions relative to treatment

7. FINANCIAL DOCUMENTATION
- Extract all billing information by provider
- Note unusually high charges with specific amounts
- Compare to regional standards where possible
- Insurance payments and outstanding balances
- Document medical equipment charges (TENS, DME)

QUALITY CONTROL FLAGS

Identify and highlight:
- Date discrepancies between records
- Missing provider credentials or qualifications
- Incomplete documentation (missing follow-ups, assessments)
- Conflicting information between providers
- Billing anomalies or excessive charges
- Treatment gaps or unexplained delays
- Missing standard medical assessments

LEGAL INTERROGATORY INTEGRATION

If legal documents are included:
- Extract employment information and wage claims
- Prior injury history denials
- Patient statements about incident mechanism
- Litigation history and other claims

OUTPUT FORMAT REQUIREMENTS

Structure your analysis as follows:

1. Record Review: (Chronological narrative format)
2. Critical Case Elements (bullet points)
3. Diagnostic Findings Hierarchy (objective vs subjective)
4. Medical Bills Analysis (with cost anomaly flags)
5. Quality Control Observations ("Of note" sections)

ANALYSIS INSTRUCTIONS

- Be extremely detail-oriented - extract specific measurements, test results, pain levels
- Maintain chronological organization while cross-referencing related findings
- Use medical terminology precisely as documented
- Flag inconsistencies without making assumptions about causes
- Quantify findings (degrees of motion loss, pain scales, measurement specifics)
- Note documentation quality and completeness issues
- Extract verbatim quotes for key medical opinions and causation statements

SPECIAL HANDLING FOR:

- Handwritten notes: Transcribe legible portions, note illegible sections
- Images/Charts: Describe visual findings, measurements, annotations
- Multiple providers: Cross-reference findings between providers
- Billing records: Extract exact amounts and service codes

IMPORTANT: Start your analysis with "=== ANALYSIS OF {os.path.basename(pdf_file)} ==="""
                                    }
                                ]
                            }
                        ]
                    )
                )
            )

        # Create the message batch
        message_batch = client.messages.batches.create(requests=batch_requests)

        # Poll for batch completion
        batch_id = message_batch.id
        while True:
            batch_status = client.messages.batches.retrieve(batch_id)
            if batch_status.processing_status == "ended":
                break
            elif batch_status.processing_status == "failed":
                return f"Batch processing failed: {batch_status.processing_status}"

            # Wait before checking again
            time.sleep(10)

        # Retrieve and combine results
        combined_analysis = f"COMPREHENSIVE MEDICAL-LEGAL ANALYSIS\n\nTotal Documents Analyzed: {len(pdf_files)}\n\n"

        results = list(client.messages.batches.results(batch_id))

        for result in results:
            if result.result.type == "succeeded":
                analysis_text = result.result.message.content[0].text
                combined_analysis += analysis_text + "\n\n" + "="*80 + "\n\n"
            else:
                combined_analysis += f"Error processing document {result.custom_id}: {result.result.error}\n\n"

        # Add summary section
        combined_analysis += "\n\nCOMPREHENSIVE CASE SUMMARY\n" + "="*50 + "\n"
        combined_analysis += f"Analysis completed for {len(pdf_files)} medical documents using Claude's Messages Batch API.\n"
        combined_analysis += "This combined analysis provides a comprehensive view of all submitted medical records.\n"

        return combined_analysis

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
    gr.Markdown("# 🏥 Medical PDF Legal Analysis Tool")
    gr.Markdown("Upload multiple medical PDF documents to generate a comprehensive legal analysis summary using Claude's Messages Batch API.")
    
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