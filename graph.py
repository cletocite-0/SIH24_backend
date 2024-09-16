import os
import PyPDF2
import google.generativeai as genai
from pathlib import Path
import tempfile
import subprocess
import firebase_admin
from firebase_admin import credentials, storage
import uuid 

# Configure Firebase
FIREBASE_CREDENTIALS_PATH = 'firebase_cred.json'
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred, {'storageBucket': 'store-graph.appspot.com'})
bucket = storage.bucket()

# Configure Gemini with API Key
GOOGLE_API_KEY = "AIzaSyC5gv15479xiPka5pH4iYgphdPyrFKDuz4"
genai.configure(api_key=GOOGLE_API_KEY)

# Step 1: Extract text from PDF
def extract_pdf_text(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    print("PDF Text Extracted")
    return text

# Step 2: Send user query and PDF text to Gemini
def send_to_gemini(pdf_text, user_query, save_dir, file_name):
    prompt = f"""
    You are given the following data from a PDF: {pdf_text}
    Based on the user's query: '{user_query}', provide executable Python code using matplotlib to generate the graph requested.
    
    The code should:
    1. Set a larger figure size to ensure all details are visible, e.g., figsize=(12, 8) or larger.
    2. Use a higher DPI to improve the image quality, e.g., dpi=150 or higher.
    3. Rotate x-axis labels by 45 degrees to avoid overlap and ensure readability, using plt.xticks(rotation=45, ha='right').
    4. Adjust x-axis label spacing if necessary to prevent overlap. Use plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=10)) or similar.
    5. Include plt.savefig() to save the graph to the folder '{save_dir}' with the filename '{file_name}'.
    6. Ensure the code is valid and will produce a clear, detailed graph.
    7. Dont include plt.show() anytime

    Only return valid Python code. Do not include explanations or numbered instructions, just the Python code snippet.
    """
    
    # Use Gemini API to get graph generation instructions
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    desc_promt = f'''
    {response} this is the response give me only a 3 line description that talks about the graph data in breif
    '''
    desc_response = model.generate_content(desc_promt).text.strip()
        
    
    # Extract the code part (clean response)
    code_snippet = response.text.strip()
    print("Gemini Response Fetched")
    return code_snippet,desc_response

# Step 3: Create and store the graph using matplotlib
def create_graph(instructions, file_path):
    # Clean the code snippet
    cleaned_instructions = instructions.replace('```python', '').replace('```', '').strip()
    
    # Print the cleaned instructions for debugging
    print("Cleaned Instructions")
    
    # Create a temporary file to hold the cleaned code snippet
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
        temp_file.write(cleaned_instructions.encode('utf-8'))
        temp_file_path = temp_file.name
    
    try:
        # Execute the code from the temporary file
        result = subprocess.run(['python', temp_file_path], capture_output=True, text=True)
        
        # Check if there were any errors during execution
        if result.returncode != 0:
            print(f"Error executing the code:\n{result.stderr}")
            return None
        
        print(f"Graph successfully generated and saved to {file_path}.")
        return file_path
    except Exception as e:
        print(f"Error generating the graph: {e}")
        return None
    finally:
        # Ensure the temporary file is removed even if an error occurs
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# Step 4: Upload the graph to Firebase Storage and get the download URL
def upload_to_firebase(file_path, bucket_name):
    # Generate a unique file name using UUID
    unique_file_name = f"graphs/{uuid.uuid4().hex}.png"
    
    blob = bucket.blob(unique_file_name)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url

# Step 5: Main function to orchestrate everything
def main():
    pdf_path = "meeting.pdf"
    user_query = input("Describe the type of graph you want: ")
    
    # Define the save directory and filename
    graph_dir = Path("./graph_img")
    graph_dir.mkdir(parents=True, exist_ok=True)
    file_name = "output_graph.png"
    file_path = graph_dir / file_name

    # Extract text from PDF
    pdf_text = extract_pdf_text(pdf_path)

    # Send to Gemini for graph instructions
    graph_instructions,description = send_to_gemini(pdf_text, user_query, graph_dir, file_name)
    # print(f"Gemini provided instructions:\n{graph_instructions}")

    # Generate and save the graph
    generated_file_path = create_graph(graph_instructions, file_path)

    if generated_file_path:
        # Upload the graph to Firebase and get the download URL
        public_url = upload_to_firebase(generated_file_path, 'your-firebase-storage-bucket')
        print(f"Graph uploaded to Firebase. Accessible at: {public_url}")
        print(f"Graph Description: {description}")

if __name__ == "__main__":
    main()