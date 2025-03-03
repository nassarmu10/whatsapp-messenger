import streamlit as st
import pandas as pd
import requests
import time
import base64

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
        # Handle NaN or None values
        if pd.isna(phone) or phone is None:
            return None
            
        # Convert to string if it's a number
        phone_str = str(phone).strip()
        
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
        """
        if not self.base_url or not self.api_token:
            raise ValueError("UltraMsg credentials not configured")
            
        # Format phone number
        formatted_phone = self._format_phone(to)
        if not formatted_phone:
            raise ValueError("Invalid phone number")
            
        url = f"{self.base_url}/messages/chat"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        payload = {
            'token': self.api_token,
            'to': formatted_phone,
            'body': message
        }
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        return response.json()
    
    def send_image(self, to, image_url, caption=None):
        """
        Send an image using UltraMsg API
        """
        if not self.base_url or not self.api_token:
            raise ValueError("UltraMsg credentials not configured")
            
        # Format phone number
        formatted_phone = self._format_phone(to)
        if not formatted_phone:
            raise ValueError("Invalid phone number")
            
        url = f"{self.base_url}/messages/image"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        payload = {
            'token': self.api_token,
            'to': formatted_phone,
            'image': image_url
        }
        
        if caption:
            payload['caption'] = caption
        
        response = requests.post(url, headers=headers, data=payload)
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
        return response.json()

def clean_phone_numbers(df):
    """
    Properly clean and format phone numbers in the dataframe
    """
    if 'phone' in df.columns:
        # Remove rows with missing phone numbers
        df = df.dropna(subset=['phone'])
        
        # Define phone formatting function
        def format_phone(phone):
            phone_str = str(phone)
            clean_phone = ''.join(char for char in phone_str if char.isdigit() or char == '+')
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone
            return clean_phone
            
        # Apply the function to the phone column
        df['phone'] = df['phone'].apply(format_phone)
    
    return df

def apply_index_range(df, start_index=None, end_index=None):
    """
    Select rows by index range
    """
    if start_index is not None and end_index is not None and start_index >= 0 and end_index >= start_index:
        # Cap end_index to avoid out of bounds errors
        end_index = min(end_index, len(df) - 1)
        # Select rows by index range (inclusive)
        return df.iloc[start_index:end_index + 1]
    return df

def get_csv_download_link(df, filename="selected_customers.csv"):
    """Generate a download link for the customers"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download Selected Customers CSV</a>'
    return href

def main():
    st.set_page_config(
        page_title="WhatsApp Messenger",
        page_icon="💬",
        layout="wide"
    )
    
    st.title("📱 WhatsApp Messaging Tool")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API credentials
        with st.expander("UltraMsg API Credentials", expanded=True):
            instance_id = st.text_input("Instance ID", value=st.session_state.get('instance_id', ''))
            api_token = st.text_input("API Token", value=st.session_state.get('api_token', ''), type="password")
            
            if instance_id:
                st.session_state['instance_id'] = instance_id
            if api_token:
                st.session_state['api_token'] = api_token
                
            if instance_id and api_token:
                st.success("API credentials configured")
            else:
                st.warning("Please configure your UltraMsg API credentials")
        
        # Sample data option
        if st.button("Load Sample Data"):
            sample_data = {
                "phone": ["+1234567890", "+1987654321", "+1122334455", "+1555666777", "+1999888777", "+1777888999"]
            }
            sample_df = pd.DataFrame(sample_data)
            # Make sure phone numbers are correctly formatted
            sample_df = clean_phone_numbers(sample_df)
            st.session_state['df'] = sample_df
            st.success("Sample data loaded!")
    
    # Main content columns
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("1️⃣ Upload Customer Data")
        
        uploaded_file = st.file_uploader("Upload a CSV file with phone numbers", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file, dtype={'phone': str})
                
                if 'phone' not in df.columns:
                    st.error("CSV must contain a 'phone' column")
                else:
                    # Clean and format phone numbers
                    df = clean_phone_numbers(df)
                    
                    if len(df) == 0:
                        st.error("No valid phone numbers found in the CSV")
                    else:
                        st.success("Data uploaded successfully!")
                        st.session_state['df'] = df
                        
                        with st.expander("Preview Data"):
                            st.dataframe(df)
            except Exception as e:
                st.error(f"Error reading CSV: {str(e)}")
        
        if 'df' in st.session_state:
            st.subheader("2️⃣ Select Phone Numbers by Index Range")
            
            with st.form(key="range_form"):
                # Index range selection
                col_range1, col_range2 = st.columns(2)
                with col_range1:
                    start_index = st.number_input(
                        "Start index:", 
                        min_value=0, 
                        max_value=len(st.session_state['df'])-1,
                        value=0
                    )
                with col_range2:
                    end_index = st.number_input(
                        "End index:", 
                        min_value=start_index, 
                        max_value=len(st.session_state['df'])-1,
                        value=min(start_index + 9, len(st.session_state['df'])-1)
                    )

                # Show how many entries will be selected
                num_selected = end_index - start_index + 1
                st.info(f"This will select {num_selected} phone numbers (indices {start_index} to {end_index})")
                
                submit_button = st.form_submit_button(label="Select Phone Numbers")
            
            if submit_button:
                # Apply index range selection
                selected_df = apply_index_range(
                    st.session_state['df'],
                    start_index=start_index,
                    end_index=end_index
                )
                
                st.session_state['selected_df'] = selected_df
                st.success(f"Selected {len(selected_df)} phone numbers")
    
    with col2:
        if 'selected_df' in st.session_state and len(st.session_state['selected_df']) > 0:
            st.header("3️⃣ Selected Phone Numbers")
            
            # Display selected phone numbers
            st.dataframe(st.session_state['selected_df'])
            st.write(f"**{len(st.session_state['selected_df'])} phone numbers selected**")
            st.markdown(get_csv_download_link(st.session_state['selected_df']), unsafe_allow_html=True)
            
            st.header("4️⃣ Send Messages")
            
            # Message tabs
            message_tab, image_tab = st.tabs(["Text Message", "Image Message"])
            
            with message_tab:
                text_message = st.text_area(
                    "Enter your message:",
                    "Hello! We have a special offer for you!"
                )
                
                # Batch settings
                col_batch1, col_batch2 = st.columns(2)
                with col_batch1:
                    batch_size = st.number_input("Batch size:", min_value=1, max_value=50, value=25)
                with col_batch2:
                    delay_seconds = st.number_input("Seconds between messages:", min_value=1, max_value=10, value=3)
                
                if st.button("Send Text Messages", disabled=not (instance_id and api_token)):
                    if not (instance_id and api_token):
                        st.error("Please configure your UltraMsg API credentials")
                    else:
                        messenger = UltraMsgWhatsAppMessenger(instance_id, api_token)
                        progress_bar = st.progress(0)
                        status_placeholder = st.empty()
                        
                        sent_count = 0
                        error_count = 0
                        total = len(st.session_state['selected_df'])
                        errors = []  # Track specific errors
                        
                        # Break into batches
                        batches = []
                        for i in range(0, total, batch_size):
                            batch_end = min(i + batch_size, total)
                            batches.append(st.session_state['selected_df'].iloc[i:batch_end])
                        
                        # Process each batch
                        for batch_idx, batch in enumerate(batches):
                            status_placeholder.write(f"Sending batch {batch_idx+1} of {len(batches)}...")
                            
                            # Send to each recipient in batch
                            for _, row in batch.iterrows():
                                try:
                                    phone = row.get('phone', '')
                                    
                                    if not phone or pd.isna(phone):
                                        error_count += 1
                                        continue
                                    
                                    # Send message
                                    messenger.send_message(phone, text_message)
                                    sent_count += 1
                                    
                                except Exception as e:
                                    error_count += 1
                                    # Add to errors list but keep going
                                    phone = row.get('phone', 'Unknown')
                                    errors.append(f"Error with {phone}: {str(e)}")
                                
                                # Update progress
                                progress_bar.progress((sent_count + error_count) / total)
                                
                                # Delay between messages
                                time.sleep(delay_seconds)
                            
                            # Add delay between batches if not the last batch
                            if batch_idx < len(batches) - 1:
                                batch_delay = max(5, delay_seconds * 2)  # At least 5 seconds between batches
                                status_placeholder.write(f"Waiting {batch_delay} seconds before next batch...")
                                time.sleep(batch_delay)
                        
                        # Show final summary
                        status_placeholder.write(f"Completed! Sent {sent_count} messages successfully with {error_count} failures.")
                        
                        # Show errors if any (expandable)
                        if errors:
                            with st.expander(f"Show {len(errors)} errors"):
                                for error in errors:
                                    st.error(error)
            
            with image_tab:
                image_method = st.radio(
                    "Image source:",
                    ["Upload image", "Image URL"],
                    horizontal=True
                )
                
                uploaded_image = None
                image_url = None
                
                if image_method == "Upload image":
                    uploaded_image = st.file_uploader("Upload an image:", type=["jpg", "jpeg", "png", "gif"])
                    if uploaded_image:
                        st.image(uploaded_image, width=200, caption="Preview of uploaded image")
                else:
                    image_url = st.text_input("Image URL:", placeholder="https://example.com/image.jpg")
                    if image_url:
                        st.image(image_url, width=200, caption="Preview of image URL")
                
                caption = st.text_input("Image Caption (optional):")
                
                # Batch settings
                col_batch1, col_batch2 = st.columns(2)
                with col_batch1:
                    batch_size = st.number_input("Batch size:", min_value=1, max_value=50, value=20, key="img_batch_size")
                with col_batch2:
                    delay_seconds = st.number_input("Seconds between messages:", min_value=1, max_value=10, value=3, key="img_delay")
                
                if st.button("Send Image Messages", disabled=not (instance_id and api_token)):
                    if (image_method == "Upload image" and not uploaded_image) or (image_method == "Image URL" and not image_url):
                        st.error("Please provide an image to send")
                    elif not (instance_id and api_token):
                        st.error("Please configure your UltraMsg API credentials")
                    else:
                        messenger = UltraMsgWhatsAppMessenger(instance_id, api_token)
                        progress_bar = st.progress(0)
                        status_placeholder = st.empty()
                        
                        sent_count = 0
                        error_count = 0
                        total = len(st.session_state['selected_df'])
                        errors = []  # Track specific errors
                        
                        # OPTIMIZATION: Upload the image once at the beginning if using "Upload image"
                        cached_media_url = None
                        if image_method == "Upload image" and uploaded_image:
                            status_placeholder.write("Uploading image to media server (this will be done only once)...")
                            try:
                                # Get image data
                                image_data = uploaded_image.getvalue()
                                image_type = uploaded_image.type
                                
                                # Upload to UltraMsg media server
                                upload_url = f"https://api.ultramsg.com/{instance_id}/media/upload"
                                
                                # Get file extension from MIME type
                                ext = image_type.split('/')[-1]
                                filename = f"image.{ext}"
                                
                                # Prepare multipart form data for upload
                                files = {
                                    'file': (filename, image_data, image_type)
                                }
                                
                                upload_data = {
                                    'token': api_token
                                }
                                
                                # Upload the image
                                upload_response = requests.post(upload_url, data=upload_data, files=files)
                                
                                if upload_response.status_code != 200:
                                    st.error(f"Failed to upload image: {upload_response.text}")
                                    st.stop()
                                
                                # Get the media URL from response
                                upload_result = upload_response.json()
                                
                                # Extract URL (success key is used by UltraMsg)
                                if 'url' in upload_result:
                                    cached_media_url = upload_result['url']
                                elif 'success' in upload_result:
                                    cached_media_url = upload_result['success']
                                else:
                                    st.error(f"Media upload did not return a URL: {upload_response.text}")
                                    st.stop()
                                
                                status_placeholder.write(f"Image uploaded successfully. Now sending to {total} recipients...")
                                
                            except Exception as e:
                                st.error(f"Error uploading image: {str(e)}")
                                st.stop()
                        
                        # Break into batches
                        batches = []
                        for i in range(0, total, batch_size):
                            batch_end = min(i + batch_size, total)
                            batches.append(st.session_state['selected_df'].iloc[i:batch_end])
                            
                        # Process each batch
                        for batch_idx, batch in enumerate(batches):
                            status_placeholder.write(f"Sending batch {batch_idx+1} of {len(batches)}...")
                            
                            # Send to each recipient in batch
                            for _, row in batch.iterrows():
                                try:
                                    phone = row.get('phone', '')
                                    
                                    if not phone or pd.isna(phone):
                                        error_count += 1
                                        continue
                                    
                                    # Send image based on selected method
                                    if image_method == "Upload image" and cached_media_url:
                                        # Use the cached media URL instead of re-uploading
                                        messenger.send_image(
                                            phone, 
                                            cached_media_url, 
                                            caption
                                        )
                                    elif image_url:
                                        messenger.send_image(
                                            phone, 
                                            image_url, 
                                            caption
                                        )
                                    else:
                                        error_count += 1
                                        continue
                                    
                                    sent_count += 1
                                    
                                except Exception as e:
                                    error_count += 1
                                    # Add to errors list but keep going
                                    phone = row.get('phone', 'Unknown')
                                    errors.append(f"Error with {phone}: {str(e)}")
                                
                                # Update progress
                                progress_bar.progress((sent_count + error_count) / total)
                                
                                # Delay between messages
                                time.sleep(delay_seconds)
                            
                            # Add delay between batches if not the last batch
                            if batch_idx < len(batches) - 1:
                                batch_delay = max(5, delay_seconds * 2)  # At least 5 seconds between batches
                                status_placeholder.write(f"Waiting {batch_delay} seconds before next batch...")
                                time.sleep(batch_delay)
                        
                        # Show final summary
                        status_placeholder.write(f"Completed! Sent {sent_count} images successfully with {error_count} failures.")
                        
                        # Show errors if any (expandable)
                        if errors:
                            with st.expander(f"Show {len(errors)} errors"):
                                for error in errors:
                                    st.error(error)
        
        elif 'df' in st.session_state:
            st.info("Select phone numbers using the index range on the left panel")
        else:
            st.info("Please upload a CSV with phone numbers or load sample data to begin")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888;">
            <small>WhatsApp Customer Messaging Tool</small>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
