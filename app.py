import os
import base64
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdf2image
from PIL import Image 
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the Generative AI model with the API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input_text, pdf_content[0], prompt])
    return response.text

def process_pdf(uploaded_file):
    # Convert the uploaded PDF to an image
    images = pdf2image.convert_from_bytes(uploaded_file.read())

    # Get the first page of the PDF
    first_page = images[0]

    # Convert the image to a byte array
    img_byte_arr = io.BytesIO()
    first_page.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    # Encode the image in base64
    pdf_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(img_byte_arr).decode()  # encode to base64
    }
    
    return [pdf_part]

@app.route('/api/analyze', methods=['POST'])
def analyze_resume():
    try:
        # Get the job description and resume from the request
        job_description = request.json.get('job_description')
        resume_base64 = request.json.get('resume')
        analysis_type = request.json.get('analysis_type')
        
        # Decode the base64-encoded resume
        resume_bytes = base64.b64decode(resume_base64)
        resume_file = io.BytesIO(resume_bytes)
        
        # Process the resume PDF
        pdf_content = process_pdf(resume_file)
        
        # Define the prompt based on analysis type
        if analysis_type == "tell_me_about_resume":
            input_prompt = """
            As a seasoned Technical HR Manager, you have a keen eye for detail and an understanding of what makes a candidate stand out. Analyze the provided resume in relation to the job description and craft a professional review in HTML format(use only text tags, list tags,table tags). Your evaluation should include:
            - **Strengths**: Highlight key strengths that make the candidate a good fit.
            - **Weaknesses**: Identify areas where the candidate's resume might fall short.
            - **Recommendations**: Offer actionable advice on how the candidate can enhance their application.
            Present your findings in a well-organized HTML format that makes it easy to digest and understand the candidate's alignment with the role.
            Note:the headings(strenghts, weaknesses, Recommendations) should have its own box or table
            Ensure your response is formatted in HTML for clear presentation and easy integration into the application.
            """
        elif analysis_type == "percentage_match":
            input_prompt = """
            As an expert ATS scanner, your mission is to decode the compatibility of the resume with the job description. Analyze the provided documents and deliver your insights in HTML format. Include:
            - **Percentage Match**: Provide a precise percentage indicating how well the resume aligns with the job description.
            - **Missing Keywords**: List keywords or phrases that are absent but critical for the role.
            - **Overall Thoughts**: Share your comprehensive view on the candidate's suitability for the position.
            """
        else:
            return jsonify({"error": "Invalid analysis type"}), 400
        
        # Get the response from the Gemini model
        response_text = get_gemini_response(job_description, pdf_content, input_prompt)
        
        # Return the response as JSON
        return jsonify({"result": response_text})
    
    except Exception as e:
        app.logger.error(f"Error analyzing resume: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
