import anthropic
import base64
import httpx
from config import ANTHROPIC_API_KEY

# First, load and encode the PDF 
#pdf_url = "https://assets.anthropic.com/m/1cd9d098ac3e6467/original/Claude-3-Model-Card-October-Addendum.pdf"
#pdf_data = base64.standard_b64encode(httpx.get(pdf_url).content).decode("utf-8")

# Alternative: Load from a local file
with open("/Users/chasefagen/Downloads/Medical Records (1) 10-06-24 thru 10-31-24.pdf", "rb") as f:
    pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

# Send to Claude using base64 encoding
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
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
                    "text": """You are a specialized medical-legal document reviewer. Analyze the
  provided medical chart PDF(s) and generate a comprehensive legal summary
  following the exact format and analytical depth demonstrated in
  professional medical record reviews.

  EXTRACTION REQUIREMENTS

  1. INCIDENT DOCUMENTATION
  - Extract ALL accident/incident details: date, time, mechanism of injury,
  location
  - Identify any date discrepancies between reports
  - Note damage estimates, emergency services involvement, airbag deployment
  - Flag conflicting accounts of how incident occurred
  - Extract witness statements or police report references

  2. CHRONOLOGICAL TIMELINE CONSTRUCTION
  - Organize all medical encounters in strict chronological order
  - Include: Date, Provider, Facility, Visit type (initial, follow-up,
  diagnostic)
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

  - Be extremely detail-oriented - extract specific measurements, test
  results, pain levels
  - Maintain chronological organization while cross-referencing related
  findings
  - Use medical terminology precisely as documented
  - Flag inconsistencies without making assumptions about causes
  - Quantify findings (degrees of motion loss, pain scales, measurement
  specifics)
  - Note documentation quality and completeness issues
  - Extract verbatim quotes for key medical opinions and causation
  statements

  SPECIAL HANDLING FOR:

  - Handwritten notes: Transcribe legible portions, note illegible sections
  - Images/Charts: Describe visual findings, measurements, annotations
  - Multiple providers: Cross-reference findings between providers
  - Billing records: Extract exact amounts and service codes"""
                }
            ]
        }
    ],
)

print(message.content)

# Save the output to a markdown file
with open("medical_analysis_output.md", "w") as f:
    f.write(message.content[0].text)



