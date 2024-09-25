import os
import time
import pandas as pd
import streamlit as st
from pdf2image import convert_from_path
from PIL import Image
import re
from tabulate import tabulate
from fuzzywuzzy import process  # Install fuzzywuzzy for fuzzy matching
import pytesseract

# Define document types and their associated keywords
document_keywords = {
    "E-Stamp": ["Certificate No", "Certificate Issue Date", "Unique Document Reference", "Purchased By", "Property Description", "First Party", "Second Party"],
    "Agreement to Flat (Kararnama)": ["Dated", "Between", "AND", "Certificate No", "Flat No", "Sale Agreement", "Sale Deed", "Agreement Date", "Kararnama"],
    "Commencement Certificate": ["Application No", "Dated", "Plot No", "Situated at", "Building Commencement", "Commencement Certificate"],
    "CIDCO Certificate": ["CIDCO No", "Date", "Tenement Number", "Tenement Transfer Order", "Challan No", "House No", "Name"],
    "Sale Deed": ["Dated", "Between", "AND", "Certificate No", "File No", "Day Book No", "Schedule C", "Schedule D", "Sale Deed No", "Sale Deed Date"],
    "Agreement to Sale": ["Dated", "Certificate No", "File No", "Day Book No", "Schedule C", "Schedule D", "Sale Deed No", "Sale Deed Date", "BETWEEN", "SPECIFICATIONS", "VENDOR", "PURCHASER"]
}

def pdf_to_images(pdf_path, dpi=300):
    """Convert PDF to a list of images, one per page."""
    images = convert_from_path(pdf_path, dpi=dpi)
    return images

def ocr_image(image):
    """Extract text from a single image using Tesseract."""
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(pdf_path):
    """Extract text from all pages of a PDF."""
    images = pdf_to_images(pdf_path)
    extracted_text = ""

    for i, image in enumerate(images):
        page_text = ocr_image(image)
        extracted_text += page_text + "\n\n"  # Add space between pages

    return extracted_text.strip()  # Strip leading/trailing whitespace

def classify_document(text, document_keywords, min_keyword_matches=2):
    """Classify the document based on the presence of keywords."""
    text_lower = text.lower()
    doc_matches = {}

    for doc_type, keywords in document_keywords.items():
        match_count = sum(1 for keyword in keywords if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower))
        if match_count >= min_keyword_matches:
            doc_matches[doc_type] = match_count

    if doc_matches:
        return max(doc_matches, key=doc_matches.get)
    return "Unknown"

def extract_keywords_based_on_document(text, document_type):
    """Extract key values from the document based on its classified type."""
    keyword_patterns = {}
    
    # Example for "E-Stamp" (add other types similarly)
    if document_type == "E-Stamp":
        keyword_patterns = {
            "Certificate No.": r"certificate\s*no\.?\s*[:\-]?\s*([^\n]+)",
            "Certificate Issued Date": r"certificate\s*issued\s*date\s*[:\-]?\s*([^\n]+)",
            "Unique Doc Reference": r"unique\s*document\s*reference\s*[:\-]?\s*([^\n]+)",
            "Purchased By": r"purchased\s*by\s*[:\-]?\s*([^\n]+)",
            "Property Description": r"property\s*description\s*[:\-]?\s*([^\n]+)",
            "First Party": r"first\s*party\s*[:\-]?\s*([^\n]+)",
            "Second Party": r"second\s*party\s*[:\-]?\s*([^\n]+)",
        }
    elif document_type == "Agreement to Flat (Kararnama)":
        keyword_patterns = {
            "SELLER": r"seller[:\s]*([^\n]+)",
            "BUYER": r"buyer[:\s]*([^\n]+)",
            "Flat No": r"flat no[:\s]*([^\n]+)",
            "Address": r"address[:\s]*([^\n]+)",
            "Area": r"area[:\s]*([^\n]+)",
            "North": r"north[:\s]*([^\n]+)",
            "South": r"south[:\s]*([^\n]+)",
            "East": r"east[:\s]*([^\n]+)",
            "West": r"west[:\s]*([^\n]+)"
        }
    elif document_type == "CIDCO Certificate":
        keyword_patterns = {
            "Mr./Mrs.": r"(?:mr\.|mrs\.)\s*[:\-]?\s*([^\n]+)",
            "CIDCO No": r"cidco\s*no\s*[:\-]?\s*([^\n]+)",
            "Date": r"date\s*[:\-]?\s*([^\n]+)",
            "Shri/Smt.": r"(?:shri|smt)\.\s*[:\-]?\s*([^\n]+)",
            "House No": r"house\s*no\s*[:\-]?\s*([^\n]+)",
            "Letter No.": r"letter\s*no\.\s*[:\-]?\s*([^\n]+)",
            "Challan No.": r"challan\s*no\s*[:\-]?\s*([^\n]+)"
        }
    elif document_type in ["Sale Deed", "Agreement to Sale"]:
        keyword_patterns = {
            "Dated": r"dated[\.:,-]?\s*([^\n,]+)",
            "Between": r"between[\.:,-]?\s*([^\n,]+)\s*and",
            "AND": r"and[\.:,-]?\s*([^\n,]+)",
            "Certificate No": r"certificate\s*no[\.:,-]?\s*([^\n,]+)",
            "File No": r"file\s*no[\.:,-]?\s*([^\n,]+)",
            "Day Book No": r"day\s*book\s*no[\.:,-]?\s*([^\n,]+)",
            "Schedule C": r"schedule\s*c[\.:,-]?\s*([^\n,]+)",
            "Schedule D": r"schedule\s*d[\.:,-]?\s*([^\n,]+)",
            "Sale Deed No": r"sale\s*deed\s*no[\.:,-]?\s*([^\n,]+)",
            "Sale Deed Date": r"sale\s*deed\s*date[\.:,-]?\s*([^\n,]+)"
        }
    elif document_type == "Commencement Certificate":
        keyword_patterns = {
            "Application No.": r"application\s*no[\.:,-]?\s*([^\n,]+)",
            "Dated": r"dated[\.:,-]?\s*([^\n,]+)",
            "Plot No.": r"plot\s*no[\.:,-]?\s*([^\n,]+)",
            "Situated at": r"situated\s*at[\.:,-]?\s*([^\n,]+)"
        }

    extracted_data = {}
    for keyword, pattern in keyword_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)  # Ignore case for matching
        extracted_data[keyword] = matches[0].strip() if matches else "Not Found"

    return extracted_data

def process_pdf(pdf_file):
    """Extract text from a PDF, classify the document, and extract keywords."""
    pdf_path = pdf_file.name
    
    # Save the uploaded file to a temporary directory
    temp_pdf_path = f"temp_{pdf_file.name}"
    with open(temp_pdf_path, "wb") as f:
        f.write(pdf_file.getbuffer())

    extracted_text = extract_text_from_pdf(temp_pdf_path)

    # Classify document and extract keywords
    document_type = classify_document(extracted_text, document_keywords)
    keyword_data = extract_keywords_based_on_document(extracted_text, document_type)

    property_description = keyword_data.get("Property Description", "Not Found")
    
    # Optionally, delete the temporary file after processing
    os.remove(temp_pdf_path)

    return document_type, keyword_data, property_description

def main():
    st.title("Smart STR Generator")
    
    st.sidebar.title("Smart STR Generator")

    uploaded_pdfs = st.file_uploader("Upload multiple PDF files", type='pdf', accept_multiple_files=True)
    uploaded_excels = st.file_uploader("Upload multiple Excel files", type='xlsx', accept_multiple_files=True)

    if st.button("Generate"):
        if uploaded_pdfs and uploaded_excels:
            summary_data = []
            for pdf_file in uploaded_pdfs:
                document_type, keyword_data, property_description = process_pdf(pdf_file)
                summary_data.append((pdf_file.name, document_type, keyword_data, property_description))

            output_text = "Summary of processed PDF files:\n\n"
            for pdf, doc_type, keyword_data, property_description in summary_data:
                output_text += f"PDF: {pdf}\n"
                output_text += f"Document Type: {doc_type}\n"
                output_text += "Extracted Keywords:\n"
                for key, value in keyword_data.items():
                    output_text += f"{key}: {value}\n"
                output_text += f"Property Description: {property_description}\n\n"

            # Display the output
            st.text_area("Output", output_text, height=300)

            # Optional: Save to text file
            with open("output_log.txt", "w") as log_file:
                log_file.write(output_text)

            st.success("Output has been logged to output_log.txt")
        else:
            st.error("Please upload both PDF and Excel files.")

if __name__ == "__main__":
    main()
