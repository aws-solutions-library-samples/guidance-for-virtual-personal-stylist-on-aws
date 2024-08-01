import streamlit as st
import boto3
from botocore.exceptions import ClientError
import requests
from PIL import Image
import io
import base64
import json
from streamlit_cognito_auth import CognitoAuthenticator

# Initialize the Streamlit app
st.set_page_config(page_title='Virtual Personal Stylist', layout='wide')

# Create a session object
session = boto3.Session()

# Get the default region from the session
default_region =  session.region_name #session.region_name 

# If no region is set in the configuration, set a default region
if default_region is None:
    default_region = 'us-east-1'

def get_secret(secret_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=default_region
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return secret

API_KEY = get_secret("stylistapikeysecret")
API_VALUES = get_secret("virtualstylistapikeysecret")

data = json.loads(API_VALUES)

url = data.get('apiurl')

YOUR_API_URL_TEXT = url + "text"
YOUR_API_URL_IMAGE = url + "image"
API_URL_DATABASE = url + "search"

# ID of Secrets Manager containing cognito parameters
cognito_secrets = get_secret("VirtualStylistCognitoSecrets")
cognito_secrets = json.loads(cognito_secrets)
pool_id = cognito_secrets['pool_id']
app_client_id = cognito_secrets['app_client_id']
app_client_secret = cognito_secrets['app_client_secret']

# Initialise CognitoAuthenticator
authenticator = CognitoAuthenticator(
        pool_id=pool_id,
        app_client_id=app_client_id,
        app_client_secret=app_client_secret,
    )
    
# Authenticate user, and stop here if not logged in
is_logged_in = authenticator.login()
if not is_logged_in:
    st.stop()

def logout():
    authenticator.logout()

# Sidebar for user authentication and logout
with st.sidebar:
    st.header("User Panel")
    st.text(f"Welcome, {authenticator.get_username()}")
    if st.button("Logout", key="logout_btn", on_click=logout):
        st.write("Logged out successfully.")
    st.markdown("---")  # Horizontal line

# Custom CSS for better styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

body {
    color: #e0e0e0;
    font-family: 'Roboto', sans-serif;
    background-color: #121212;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath opacity='.5' d='M96 95h4v1h-4v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4h-9v4h-1v-4H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15v-9H0v-1h15V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h9V0h1v15h4v1h-4v9h4v1h-4v9h4v1h-4v9h4v1h-4v9h4v1h-4v9h4v1h-4v9h4v1h-4v9h4v1h-4v9zm-1 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-9-10h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm9-10v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-9-10h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm9-10v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-9-10h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm9-10v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-10 0v-9h-9v9h9zm-9-10h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9zm10 0h9v-9h-9v9z'/%3E%3Cpath d='M6 5V0H5v5H0v1h5v94h1V6h94V5H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

.main {
    background-color: transparent;
}

.stButton > button {
    background-color: #BB86FC;
    color: #000000;
    border-radius: 20px;
    border: none;
    padding: 10px 24px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px rgba(187, 134, 252, 0.3);
}

.stButton > button:hover {
    background-color: #3700B3;
    color: #ffffff;
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(187, 134, 252, 0.5);
}

.stTextInput > div > div > input {
    background-color: #1F1B24;
    border: 2px solid #BB86FC;
    border-radius: 8px;
    color: #ffffff;
    padding: 12px;
}

.stTextInput > div > div > input:focus {
    box-shadow: 0 0 0 2px rgba(187, 134, 252, 0.5);
}

.stTextInput > label {
    color: #BB86FC;
    font-weight: 500;
}

.css-1y0tads {
    color: #CF6679;
}

.st-bq, .st-md, .css-1q8dd3e {
    background-color: rgba(31, 27, 36, 0.7);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(187, 134, 252, 0.1);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.st-fz {
    color: #03DAC6;
    font-weight: 700;
}

.st-hv {
    color: #BB86FC;
}

.stTabs {
    background-color: rgba(31, 27, 36, 0.7);
    border-radius: 16px;
    overflow: hidden;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(187, 134, 252, 0.1);
}

.stTabs > div > div > div {
    background-color: transparent;
}

.stTabs > div > div > div > div > div > div > div {
    background-color: #1F1B24;
    color: #BB86FC;
    font-weight: 500;
    border-radius: 8px 8px 0 0;
    padding: 10px 20px;
    margin-right: 4px;
}

.stTabs > div > div > div > div > div > div > div[aria-selected="true"] {
    background-color: #BB86FC;
    color: #000000;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-track {
    background: #1F1B24;
}

::-webkit-scrollbar-thumb {
    background: #BB86FC;
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: #3700B3;
}

/* Add a subtle glow effect to the page */
.main::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at top right, rgba(187, 134, 252, 0.1) 0%, transparent 60%);
    pointer-events: none;
    z-index: -1;
}
</style>
""", unsafe_allow_html=True)

def api_call_text(input_text):
    api_url = YOUR_API_URL_TEXT
    payload = {"query": str(input_text)}
    try:
        response = requests.get(
            api_url,
            headers={"x-api-key": str(API_KEY), "Authorization": f"Bearer {access_token}"},
            params=payload,
        )
        response.raise_for_status()  # Check for HTTP errors
        if response.text:
            return response.text
        else:
            st.error("Empty response from the API.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API call error: {e}")
        return None

def api_call_image(input_text):
    api_url = YOUR_API_URL_IMAGE
    payload = {"query": str(input_text)}
    try:
        response = requests.get(
            api_url,
            headers={"x-api-key": str(API_KEY), "Authorization": f"Bearer {access_token}"},
            params=payload,
        )
        response.raise_for_status()  # Check for HTTP errors
        if response.text:
            return response.text
        else:
            st.error("Empty response from the API.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API call error: {e}")
        return None

def api_call_database(input_text):
    api_url = API_URL_DATABASE
    payload = {"query": str(input_text)}
    try:
        response = requests.get(
            api_url,
            headers={"x-api-key": str(API_KEY), "Authorization": f"Bearer {access_token}"},
            params=payload,
        )
        response.raise_for_status()  # Check for HTTP errors
        if response.text:
            return response.json()
        else:
            st.error("Empty response from the API.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API call error: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error: {e}")
        st.write(response.text)  # Display the raw response for debugging
        return None
        
def decode_and_display_image(base64_image):
    try:
        # Decode base64 image to binary
        image_data = base64.b64decode(base64_image)
        
        # Use a with statement to manage the BytesIO object
        with io.BytesIO(image_data) as image_buffer:
            # Convert binary data to PIL Image
            image = Image.open(image_buffer)
            
            # Display the image in Streamlit with a limited width
            st.image(image, use_column_width=False, width=400, output_format='PNG')
    except Exception as e:
        st.error(f"Error decoding image: {e}")

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add a starting message from the bot
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hello! I'm your AI Personal Stylist. I can help you with personal styling, fashion advice, and provide information about fashion trends. How can I assist you today?"
    })

def display_chat():
    # Display chat history
    st.subheader("Chat History")
    for message in st.session_state.messages:
        with st.container():
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

def get_user_input(default_text=""):
    return st.text_input("Enter your query:", value=default_text)

def display_text_input_area():
    user_input = get_user_input()
    if st.button("Send", key="send_button"):
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            try:
                with st.spinner("Loading..."):
                    response = api_call_text(user_input)
                    if response:
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("Failed to get a valid response from the API.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            st.rerun()

def display_image_generation():
    user_input = get_user_input("Describe the fashion image you want to generate.")
    if st.button("Generate Image", key="generate_image_button"):
        try:
            with st.spinner("Generating image..."):
                image_data = api_call_image(user_input)
                if image_data:
                    decode_and_display_image(image_data)
                else:
                    st.warning("Please provide a valid input.")
        except Exception as e:
            st.error(f"Error generating image: {e}")

def display_database_search():
    user_input = get_user_input("Search for fashion items in the database.")
    if st.button("Search Database", key="search_database_button"):
        try:
            with st.spinner("Searching database..."):
                data = api_call_database(user_input)
                if data:
                    st.markdown("Here are some products that match your description:")
                    for item in data:
                        image_data = base64.b64decode(item['image_base64'])
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, caption=f"Similarity Score: {item['score']:.2f}, Image Key: {item['image_key']}", use_column_width=False, width=400)
                else:
                    st.error("No data returned from the API.")
        except Exception as e:
            st.error(f"Error searching database: {e}")

# Render the selected page using tabs
tabs = st.tabs(["Chat", "Generate Image", "Search Database"])

with tabs[0]:
    st.header("Chat with your AI Stylist")
    display_chat()
    display_text_input_area()
    
with tabs[1]:
    st.header("Generate Fashion Image")
    display_chat()
    display_image_generation()

with tabs[2]:
    st.header("Search Fashion Database")
    display_chat()
    display_database_search()
