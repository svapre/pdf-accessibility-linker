import fitz  # PyMuPDF
import argparse
import os

def analyze_pages(pdf_path: str, num_pages: int):
    """
    Extracts and prints the text content from the first few pages of a PDF.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at '{pdf_path}'")
        return

    try:
        doc = fitz.open(pdf_path)
        
        total_pages = len(doc)
        pages_to_read = min(num_pages, total_pages)

        print(f"Analyzing first {pages_to_read} of {total_pages} pages from '{os.path.basename(pdf_path)}'...")

        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text("text")
            
            print("\n" + "="*20 + f" PAGE {i+1} " + "="*20)
            print(text.strip())
            print("="*50)

        doc.close()

    except Exception as e:
        print(f"An error occurred while processing the PDF: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose PDF text content for analysis.")
    parser.add_argument("pdf_file", help="Path to the PDF file to analyze.")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to read from the beginning of the document.")
    
    args = parser.parse_args()
    
    analyze_pages(args.pdf_file, args.pages)
