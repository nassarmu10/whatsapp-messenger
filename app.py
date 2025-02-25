import streamlit as st
import pandas as pd
import requests
import os
import time
from datetime import datetime
import json
import base64
from io import StringIO

class UltraMsgWhatsAppMessenger:
    def __init__(self, instance_id=None, api_token=None):
        """
        Initialize the WhatsApp messenger tool using UltraMsg API
        """
        self.instance_id = instance_id
        self.api_token = api_token
        self.base_url = f"https://api.ultramsg.com/{self.instance_id}" if instance_id else None
        
    def _format_phone(self, phone):
        """
        Format phone number for WhatsApp - handles various formats properly
        """
        # Convert to string if it's a number
        phone_str = str(phone)
        
        # Remove all non-digit characters (keep + if it exists)
        clean_phone = ''.join(char for char in phone_str if char.isdigit() or char == '+')
        
        # Ensure it has a + prefix
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
            
        # For UltraMsg API: remove the + sign
        ultramsg_phone = clean_phone[1:] if clean_phone.startswith('+') else clean_phone
            
        return ultramsg_phone
    
    def send_message(self, to, message):
        """
        Send a message using UltraMsg API
        
        :param to: Recipient phone number
        :param message: Message content
        :return: API response
        """
        if not self.base_url or not self.api_token:
            raise ValueError("UltraMsg credentials not configured")
            
        url = f"{self.base_url}/messages/chat"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        # Format phone number
        formatted_phone = self._format_phone(to)
        
        payload = {
            'token': self.api_token,
            'to': formatted_phone,
            'body': message
        }
        
        # Debug info
        st.session_state['last_api_request'] = {
            'url': url,
            'to': formatted_phone,
            'original_phone': to
        }
        
        response = requests.post(url, headers=headers, data=payload)
        
        # Save response for debugging
        st.session_state['last_api_response'] = {
            'status_code': response.status_code,
            'text': response.text
        }
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
        return response.json()
    
    def send_image(self, to, image_url, caption=None):
        """
        Send an image using UltraMsg API
        
        :param to: Recipient phone number
        :param image_url: URL of the image
        :param caption: Optional caption for the image
        :return: API response
        """
        if not self.base_url or not self.api_token:
            raise ValueError("UltraMsg credentials not configured")
            
        url = f"{self.base_url}/messages/image"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        # Format phone number
        formatted_phone = self._format_phone(to)
        
        payload = {
            'token': self.api_token,
            'to': formatted_phone,
            'image': image_url
        }
        
        if caption:
            payload['caption'] = caption
        
        # Debug info
        st.session_state['last_api_request'] = {
            'url': url,
            'to': formatted_phone,
            'original_phone': to
        }
        
        response = requests.post(url, headers=headers, data=payload)
        
        # Save response for debugging
        st.session_state['last_api_response'] = {
            'status_code': response.status_code,
            'text': response.text
        }
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
        return response.json()

def clean_phone_numbers(df):
    """
    Properly clean and format phone numbers in the dataframe
    """
    if 'phone' in df.columns:
        # Use a custom function to properly format each phone
        def format_phone(phone):
            # Convert to string if it's a number
            phone_str = str(phone)
            
            # Remove all non-digit characters (keep + if it exists)
            clean_phone = ''.join(char for char in phone_str if char.isdigit() or char == '+')
            
            # Ensure it has a + prefix
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone
                
            return clean_phone
            
        # Apply the function to the phone column
        df['phone'] = df['phone'].apply(format_phone)
    
    return df

def apply_filters(df, address=None, min_spent=None, after_date=None):
    """Apply filters to the DataFrame"""
    filtered_df = df.copy()
    
    if address:
        filtered_df = filtered_df[filtered_df['address'].str.contains(address, case=False, na=False)]
    
    if min_spent is not None:
        filtered_df = filtered_df[filtered_df['total_spent'] >= min_spent]
    
    if after_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['last_purchase']) >= pd.to_datetime(after_date)]
    
    return filtered_df

def get_csv_download_link(df, filename="filtered_customers.csv"):
    """Generate a download link for the filtered customers"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download Filtered Customers CSV</a>'
    return href

def main():
    st.set_page_config(
        page_title="WhatsApp Customer Messenger",
        page_icon="💬",
        layout="wide"
    )
    
    st.title("📱 WhatsApp Customer Messaging Tool")
    st.write("Filter customers and send personalized WhatsApp messages")
    
    # Initialize session states if they don't exist
    if 'debug_mode' not in st.session_state:
        st.session_state['debug_mode'] = False
    
    if 'live_mode' not in st.session_state:
        st.session_state['live_mode'] = False
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API credentials
        with st.expander("UltraMsg API Credentials", expanded=True):
            instance_id = st.text_input("Instance ID", value=st.session_state.get('instance_id', ''), type="password")
            api_token = st.text_input("API Token", value=st.session_state.get('api_token', ''), type="password")
            
            if instance_id:
                st.session_state['instance_id'] = instance_id
            if api_token:
                st.session_state['api_token'] = api_token
                
            if instance_id and api_token:
                st.success("API credentials configured")
            else:
                st.warning("Please configure your UltraMsg API credentials")
        
        # Debug mode toggle
        st.session_state['debug_mode'] = st.checkbox("Enable Debug Mode", value=st.session_state['debug_mode'])
        
        # Sample data option
        if st.button("Load Sample Data"):
            sample_data = {
                "name": ["John Smith", "Emma Johnson", "Michael Brown", "Sophia Williams", "James Davis", "Olivia Miller"],
                "phone": ["+1234567890", "+1987654321", "+1122334455", "+1555666777", "+1999888777", "+1777888999"],
                "address": ["123 Main St, New York", "456 Oak Ave, New York", "789 Pine Rd, Boston", 
                            "101 Maple Dr, Chicago", "202 Cedar Ln, Boston", "303 Birch St, New York"],
                "last_purchase": ["2023-10-15", "2023-11-20", "2023-12-05", "2024-01-10", "2024-02-25", "2024-03-15"],
                "total_spent": [350, 520, 210, 780, 150, 430]
            }
            sample_df = pd.DataFrame(sample_data)
            # Make sure phone numbers are correctly formatted
            sample_df = clean_phone_numbers(sample_df)
            st.session_state['df'] = sample_df
            st.success("Sample data loaded!")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("1️⃣ Upload Customer Data")
        
        uploaded_file = st.file_uploader("Upload a CSV file with customer data", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                required_columns = ['name', 'phone']
                
                if not all(col in df.columns for col in required_columns):
                    st.error(f"CSV must contain columns: {', '.join(required_columns)}")
                else:
                    # Clean and format phone numbers
                    df = clean_phone_numbers(df)
                    
                    st.success("Data uploaded successfully!")
                    st.session_state['df'] = df
                    
                    with st.expander("Preview Data"):
                        # Display preview with correctly formatted data
                        st.dataframe(df)
                        
                        # In debug mode, also show raw phone numbers
                        if st.session_state['debug_mode']:
                            st.subheader("Phone Numbers (Debug View)")
                            for i, row in df.iterrows():
                                st.text(f"{row['name']}: {row['phone']}")
            except Exception as e:
                st.error(f"Error reading CSV: {str(e)}")
        
        if 'df' in st.session_state:
            st.subheader("2️⃣ Filter Customers")
            
            with st.form(key="filter_form"):
                address_filter = st.text_input("Address contains:", placeholder="e.g. New York")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    min_spent = st.number_input("Minimum amount spent:", min_value=0.0, step=10.0)
                with col_b:
                    if 'last_purchase' in st.session_state['df'].columns:
                        purchase_after = st.date_input("Purchased after:", value=None)
                    else:
                        purchase_after = None
                        st.info("'last_purchase' column not found in data")
                
                submit_button = st.form_submit_button(label="Apply Filters")
            
            if submit_button:
                # Apply filters
                filtered_df = apply_filters(
                    st.session_state['df'],
                    address=address_filter if address_filter else None,
                    min_spent=min_spent if min_spent > 0 else None,
                    after_date=purchase_after if purchase_after else None
                )
                
                st.session_state['filtered_df'] = filtered_df
                st.success(f"Filtered to {len(filtered_df)} customers")
    
    with col2:
        if 'filtered_df' in st.session_state and len(st.session_state['filtered_df']) > 0:
            st.header("3️⃣ Selected Customers")
            
            # Display selected customers
            st.dataframe(st.session_state['filtered_df'])
            
            # Debug view for selected customers
            if st.session_state['debug_mode']:
                st.subheader("Selected Phone Numbers (Debug View)")
                for i, row in st.session_state['filtered_df'].iterrows():
                    st.text(f"{row['name']}: {row['phone']}")
            
            st.markdown(get_csv_download_link(st.session_state['filtered_df']), unsafe_allow_html=True)
            
            st.header("4️⃣ Compose Message")
            
            # Global test mode toggle
            live_mode_col1, live_mode_col2 = st.columns([3, 1])
            with live_mode_col1:
                st.write("⚠️ Make sure your configuration is correct before switching to Live Mode")
            with live_mode_col2:
                live_mode = st.toggle("🔴 Live Mode", value=st.session_state['live_mode'])
                st.session_state['live_mode'] = live_mode
            
            message_tab, image_tab = st.tabs(["Text Message", "Image Message"])
            
            with message_tab:
                text_message = st.text_area(
                    "Enter your message:",
                    "Hello {name}, we have a special offer for you!",
                    help="Use {name} to insert the customer's name"
                )
                
                test_mode = not st.session_state['live_mode']
                if test_mode:
                    st.info("TEST MODE ACTIVE - Messages will not actually be sent")
                else:
                    st.warning("LIVE MODE ACTIVE - Messages will be sent to real recipients!")
                
                if st.button("Send Text Messages", key="send_text", disabled=not (instance_id and api_token)):
                    if not (instance_id and api_token):
                        st.error("Please configure UltraMsg API credentials in the sidebar")
                    else:
                        messenger = UltraMsgWhatsAppMessenger(instance_id, api_token)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        sent_count = 0
                        error_count = 0
                        total = len(st.session_state['filtered_df'])
                        
                        if test_mode:
                            # Just show what would be sent
                            for index, row in st.session_state['filtered_df'].iterrows():
                                # Personalize message
                                name = row.get('name', 'Customer')
                                personalized_message = text_message.replace('{name}', name)
                                phone = row.get('phone', '')
                                
                                status_text.write(f"Would send to {name} ({phone}):")
                                st.code(personalized_message)
                                
                                # Show how phone would be formatted for API
                                if st.session_state['debug_mode']:
                                    formatted = messenger._format_phone(phone)
                                    st.text(f"Phone would be formatted as: {formatted}")
                                
                                # Update progress
                                progress_bar.progress((index + 1) / total)
                                time.sleep(0.2)  # Slow down for visibility
                            
                            st.success("Test completed! No messages were actually sent.")
                        else:
                            # Actually send messages
                            for index, row in st.session_state['filtered_df'].iterrows():
                                try:
                                    # Personalize message
                                    name = row.get('name', 'Customer')
                                    personalized_message = text_message.replace('{name}', name)
                                    phone = row.get('phone', '')
                                    
                                    if not phone:
                                        status_text.write(f"⚠️ Missing phone number for {name}, skipping...")
                                        error_count += 1
                                        continue
                                    
                                    # Send message
                                    result = messenger.send_message(phone, personalized_message)
                                    
                                    status_text.write(f"✅ Sent to {name} ({phone})")
                                    sent_count += 1
                                    
                                    # Update progress
                                    progress_bar.progress((sent_count + error_count) / total)
                                    
                                    # Debug info
                                    if st.session_state['debug_mode'] and 'last_api_request' in st.session_state:
                                        st.json(st.session_state['last_api_request'])
                                        st.json(st.session_state['last_api_response'])
                                    
                                    # Avoid rate limiting
                                    time.sleep(1)
                                    
                                except Exception as e:
                                    status_text.write(f"❌ Error sending to {row.get('name', '')}: {str(e)}")
                                    error_count += 1
                                    
                                    # Debug info on error
                                    if st.session_state['debug_mode'] and 'last_api_request' in st.session_state:
                                        st.error(f"API Error Details:")
                                        st.json(st.session_state['last_api_request'])
                                        if 'last_api_response' in st.session_state:
                                            st.json(st.session_state['last_api_response'])
                                
                            st.success(f"Completed! Sent {sent_count} messages with {error_count} errors.")
            
            with image_tab:
                image_url = st.text_input(
                    "Image URL:",
                    placeholder="https://example.com/image.jpg"
                )
                
                caption = st.text_input(
                    "Image Caption (optional):",
                    "Check out our new products, {name}!",
                    help="Use {name} to insert the customer's name"
                )
                
                test_mode = not st.session_state['live_mode']
                if test_mode:
                    st.info("TEST MODE ACTIVE - Images will not actually be sent")
                else:
                    st.warning("LIVE MODE ACTIVE - Images will be sent to real recipients!")
                
                if st.button("Send Image Messages", key="send_image", disabled=not (instance_id and api_token)):
                    if not image_url:
                        st.error("Please enter an image URL")
                    elif not (instance_id and api_token):
                        st.error("Please configure UltraMsg API credentials in the sidebar")
                    else:
                        messenger = UltraMsgWhatsAppMessenger(instance_id, api_token)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        if test_mode:
                            # Just show what would be sent
                            for index, row in st.session_state['filtered_df'].iterrows():
                                # Personalize caption
                                name = row.get('name', 'Customer')
                                personalized_caption = caption.replace('{name}', name) if caption else None
                                phone = row.get('phone', '')
                                
                                status_text.write(f"Would send image to {name} ({phone}):")
                                st.image(image_url, width=200)
                                if personalized_caption:
                                    st.code(personalized_caption)
                                
                                # Show how phone would be formatted for API
                                if st.session_state['debug_mode']:
                                    formatted = messenger._format_phone(phone)
                                    st.text(f"Phone would be formatted as: {formatted}")
                                
                                # Update progress
                                progress_bar.progress((index + 1) / len(st.session_state['filtered_df']))
                                time.sleep(0.2)  # Slow down for visibility
                            
                            st.success("Test completed! No images were actually sent.")
                        else:
                            # Actually send images
                            sent_count = 0
                            error_count = 0
                            total = len(st.session_state['filtered_df'])
                            
                            for index, row in st.session_state['filtered_df'].iterrows():
                                try:
                                    # Personalize caption
                                    name = row.get('name', 'Customer')
                                    personalized_caption = caption.replace('{name}', name) if caption else None
                                    phone = row.get('phone', '')
                                    
                                    if not phone:
                                        status_text.write(f"⚠️ Missing phone number for {name}, skipping...")
                                        error_count += 1
                                        continue
                                    
                                    # Send image
                                    result = messenger.send_image(phone, image_url, personalized_caption)
                                    
                                    status_text.write(f"✅ Sent image to {name} ({phone})")
                                    sent_count += 1
                                    
                                    # Update progress
                                    progress_bar.progress((sent_count + error_count) / total)
                                    
                                    # Debug info
                                    if st.session_state['debug_mode'] and 'last_api_request' in st.session_state:
                                        st.json(st.session_state['last_api_request'])
                                        st.json(st.session_state['last_api_response'])
                                    
                                    # Avoid rate limiting
                                    time.sleep(1)
                                    
                                except Exception as e:
                                    status_text.write(f"❌ Error sending to {row.get('name', '')}: {str(e)}")
                                    error_count += 1
                                    
                                    # Debug info on error
                                    if st.session_state['debug_mode'] and 'last_api_request' in st.session_state:
                                        st.error(f"API Error Details:")
                                        st.json(st.session_state['last_api_request'])
                                        if 'last_api_response' in st.session_state:
                                            st.json(st.session_state['last_api_response'])
                                
                            st.success(f"Completed! Sent {sent_count} images with {error_count} errors.")
        
        elif 'df' in st.session_state:
            st.info("Apply filters to select customers for messaging")
        else:
            st.info("Please upload customer data or load sample data to begin")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888;">
            <small>WhatsApp Customer Messaging Tool — Powered by UltraMsg API</small>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
