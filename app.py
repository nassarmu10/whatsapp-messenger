import streamlit as st
import pandas as pd
import requests
import os
import time
import json
from datetime import datetime
import base64
from io import StringIO
import concurrent.futures

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
    
    def send_broadcast(self, to_numbers, message):
        """
        Send a broadcast message to multiple recipients using UltraMsg API
        
        :param to_numbers: List of recipient phone numbers
        :param message: Message content to broadcast
        :return: API response
        """
        if not self.base_url or not self.api_token:
            raise ValueError("UltraMsg credentials not configured")
            
        url = f"{self.base_url}/messages/chat"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        # Format all phone numbers
        formatted_numbers = [self._format_phone(phone) for phone in to_numbers]
        
        responses = []
        
        # UltraMsg processes multiple recipients by sending individual messages
        # This implementation sends them in parallel which is more efficient
        
        def send_single_message(formatted_phone):
            payload = {
                'token': self.api_token,
                'to': formatted_phone,
                'body': message
            }
            
            response = requests.post(url, headers=headers, data=payload)
            
            if response.status_code != 200:
                return {
                    'phone': formatted_phone,
                    'success': False,
                    'error': f"API Error {response.status_code}: {response.text}"
                }
            else:
                return {
                    'phone': formatted_phone,
                    'success': True,
                    'response': response.json()
                }
        
        # Use ThreadPoolExecutor to send messages in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_phone = {
                executor.submit(send_single_message, phone): phone 
                for phone in formatted_numbers
            }
            
            # Get results as they complete
            for future in concurrent.futures.as_completed(future_to_phone):
                phone = future_to_phone[future]
                try:
                    response = future.result()
                    responses.append(response)
                except Exception as e:
                    responses.append({
                        'phone': phone,
                        'success': False,
                        'error': str(e)
                    })
        
        return responses

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

def apply_filters(df, address=None, min_spent=None, after_date=None, limit=None):
    """Apply filters to the DataFrame with an optional limit on number of customers"""
    filtered_df = df.copy()
    
    if address:
        filtered_df = filtered_df[filtered_df['address'].str.contains(address, case=False, na=False)]
    
    if min_spent is not None:
        filtered_df = filtered_df[filtered_df['total_spent'] >= min_spent]
    
    if after_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['last_purchase']) >= pd.to_datetime(after_date)]
    
    # Apply limit if specified
    if limit and limit > 0 and limit < len(filtered_df):
        filtered_df = filtered_df.head(limit)
    
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
            instance_id = st.text_input("Instance ID", value=st.session_state.get('instance_id', ''), type="default")
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
                
                # Add limit option
                limit_customers = st.number_input(
                    "Limit to first N customers (0 = no limit):", 
                    min_value=0, 
                    max_value=len(st.session_state['df']),
                    value=0,
                    help="Set a limit to only select the first N customers after applying filters"
                )
                
                submit_button = st.form_submit_button(label="Apply Filters")
            
            if submit_button:
                # Apply filters with optional limit
                filtered_df = apply_filters(
                    st.session_state['df'],
                    address=address_filter if address_filter else None,
                    min_spent=min_spent if min_spent > 0 else None,
                    after_date=purchase_after if purchase_after else None,
                    limit=limit_customers if limit_customers > 0 else None
                )
                
                st.session_state['filtered_df'] = filtered_df
                
                # Show how many were filtered
                total_matching = len(apply_filters(
                    st.session_state['df'],
                    address=address_filter if address_filter else None,
                    min_spent=min_spent if min_spent > 0 else None,
                    after_date=purchase_after if purchase_after else None
                ))
                
                if limit_customers > 0 and limit_customers < total_matching:
                    st.success(f"Filtered to {len(filtered_df)} customers (limited from {total_matching} total matches)")
                else:
                    st.success(f"Filtered to {len(filtered_df)} customers")
    
    with col2:
        if 'filtered_df' in st.session_state and len(st.session_state['filtered_df']) > 0:
            st.header("3️⃣ Selected Customers")
            
            # Display selected customers
            st.dataframe(st.session_state['filtered_df'])
            
            # Display count
            st.write(f"**{len(st.session_state['filtered_df'])} customers selected**")
            
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
            
            # Tabs for different message types
            message_tab, image_tab, broadcast_tab = st.tabs(["Text Message", "Image Message", "Broadcast"])
            
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
                        st.error("Please configure your UltraMsg API credentials")
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
                        st.error("Please configure your UltraMsg API credentials")
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

            with broadcast_tab:
                st.subheader("Send the same message to all selected customers")
                
                broadcast_message = st.text_area(
                    "Enter your broadcast message:",
                    "Hello {name}! We have a special offer for all our customers!",
                    help="You can use {name} to personalize for each recipient"
                )
                
                # Add a way to limit the batch size to avoid rate limits
                col_batch1, col_batch2 = st.columns([1, 1])
                with col_batch1:
                    batch_size = st.number_input("Batch size (recipients per batch):", min_value=1, max_value=100, value=20)
                with col_batch2:
                    delay_between_batches = st.number_input("Seconds between batches:", min_value=1, max_value=60, value=5)
                
                test_mode = not st.session_state['live_mode']
                if test_mode:
                    st.info("TEST MODE ACTIVE - Broadcast will not actually be sent")
                else:
                    st.warning("LIVE MODE ACTIVE - Broadcast will be sent to ALL selected recipients!")
                
                if st.button("Send Broadcast", key="send_broadcast", disabled=not (instance_id and api_token)):
                    if not (instance_id and api_token):
                        st.error("Please configure your UltraMsg API credentials")
                    else:
                        messenger = UltraMsgWhatsAppMessenger(instance_id, api_token)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        total_recipients = len(st.session_state['filtered_df'])
                        recipients = st.session_state['filtered_df']
                        
                        # Display summary before proceeding
                        st.write(f"Preparing to broadcast to {total_recipients} recipients")
                        
                        # Split into batches to avoid rate limits
                        batches = []
                        for i in range(0, total_recipients, batch_size):
                            batches.append(recipients.iloc[i:i+batch_size])
                        
                        st.write(f"Split into {len(batches)} batches of up to {batch_size} recipients each")
                        
                        if test_mode:
                            # Just simulate the broadcast
                            for batch_idx, batch in enumerate(batches):
                                status_text.write(f"Processing batch {batch_idx+1} of {len(batches)}")
                                
                                # Show recipients in this batch
                                st.write(f"**Batch {batch_idx+1}** would include:")
                                for _, row in batch.iterrows():
                                    name = row.get('name', 'Customer')
                                    phone = row.get('phone', '')
                                    personalized_message = broadcast_message.replace('{name}', name)
                                    st.text(f"- {name} ({phone})")
                                
                                # Update progress
                                progress_bar.progress((batch_idx + 1) / len(batches))
                                
                                # Simulate delay between batches (shorter for demo)
                                if batch_idx < len(batches) - 1:
                                    status_text.write(f"Would wait {delay_between_batches} seconds before next batch...")
                                    time.sleep(1)  # Shorter wait for test mode
                            
                            st.success("Test completed! No messages were actually sent.")
                        else:
                            # Actually send the broadcast
                            sent_count = 0
                            error_count = 0
                            
                            for batch_idx, batch in enumerate(batches):
                                status_text.write(f"Sending batch {batch_idx+1} of {len(batches)}")
                                
                                # For each recipient, we need to personalize the message
                                for _, row in batch.iterrows():
                                    try:
                                        name = row.get('name', 'Customer')
                                        phone = row.get('phone', '')
                                        
                                        if not phone:
                                            status_text.write(f"⚠️ Missing phone number for {name}, skipping...")
                                            error_count += 1
                                            continue
                                            
                                        # Personalize message for this recipient
                                        personalized_message = broadcast_message.replace('{name}', name)
                                        
                                        # Send individual message (since we're personalizing)
                                        result = messenger.send_message(phone, personalized_message)
                                        
                                        sent_count += 1
                                        
                                        # Debug info
                                        if st.session_state['debug_mode']:
                                            st.text(f"✓ Sent to {name} ({phone})")
                                        
                                    except Exception as e:
                                        error_count += 1
                                        if st.session_state['debug_mode']:
                                            st.error(f"Error sending to {row.get('name', '')}: {str(e)}")
                                
                                # Update progress
                                progress_bar.progress((batch_idx + 1) / len(batches))
                                
                                # Wait before next batch to avoid rate limits
                                if batch_idx < len(batches) - 1:
                                    status_text.write(f"Waiting {delay_between_batches} seconds before next batch...")
                                    time.sleep(delay_between_batches)
                            
                            st.success(f"Broadcast completed!Sent to {sent_count} recipients with {error_count} errors.")
        
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
