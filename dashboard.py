import streamlit as st
import requests
import time

# Configuration
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="OptiSlot AO Dashboard", page_icon="🚗", layout="wide")

st.title("🚗 OptiSlot AO: Intelligent Gate System")
st.markdown("### Autonomous Parking Operations Center")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("Simulate a Vehicle Arrival at Gate 1")
    
    # Selection: Upload or Camera
    input_method = st.radio("Select Input Method", ["Upload Image", "Take Photo"], horizontal=True)
    
    image_file = None
    
    if input_method == "Upload Image":
        image_file = st.file_uploader("Upload Vehicle Image", type=['jpg', 'jpeg', 'png'])
    else:
         image_file = st.camera_input("Take a photo")

    if image_file is not None:
        if input_method == "Upload Image":
             st.image(image_file, caption="Camera Feed", width="stretch")
        
        if st.button("🚨 TRIGGER GATE ENTRY"):
            with st.spinner("Processing Entry Event..."):
                try:
                    # Prepare file for API
                    files = {"file": (image_file.name if hasattr(image_file, 'name') else "camera_capture.jpg", image_file.getvalue(), "image/jpeg")}
                    
                    # Call API
                    start_ts = time.time()
                    response = requests.post(f"{API_URL}/gate/GATE_01/entry", files=files)
                    latency = (time.time() - start_ts) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"Response Received in {latency:.2f}ms")
                        st.json(data)
                        
                        st.balloons()
                    else:
                        st.error(f"API Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"Connection Error: {e}")
                    st.warning("Ensure the backend is running: `uvicorn app.main:app`")

with col2:
    st.subheader("System Status")
    # Quick simulation of logs/status since we don't have a real websocket yet
    if image_file and st.session_state.get("last_trigger"):
         st.write("Checking system logs...")
    
    st.metric(label="API Latency Goal", value="< 10ms", delta="-2ms (Excellent)")
    st.markdown("---")
    st.markdown("""
    **Workflow Status:**
    1.  ✅ **Reflex**: API acknowledged request.
    2.  👁️ **Vision**: YOLOv8 Analyzing image...
    3.  🧠 **Memory**: Checking ChromaDB for history...
    4.  📦 **Optimization**: Calculating optimal slot...
    """)

    st.markdown("---")
    st.subheader("🅿️ Live Parking Lot State")
    
    col_refresh, col_reset = st.columns(2)
    
    with col_refresh:
        if st.button("🔄 Refresh State"):
            try:
                r = requests.get(f"{API_URL}/api/slots")
                if r.status_code == 200:
                    slots = r.json()
                    # Create a simple metric view
                    occupied = [s for s in slots if s['is_occupied']]
                    st.session_state['slots_data'] = slots # Cache
                    st.metric("Occupied Slots", f"{len(occupied)} / {len(slots)}")
                    
                    if occupied:
                        st.write("Recent Allocations:")
                        st.dataframe(occupied)
                    else:
                        st.info("Lot is Empty.")
            except Exception as e:
                st.error(f"Fetch Error: {e}")

    with col_reset:
        if st.button("🗑️ Reset System", type="primary"):
            try:
                r = requests.delete(f"{API_URL}/api/reset")
                if r.status_code == 200:
                    st.success("System Reset Complete! DB Cleared.")
                    time.sleep(1)
                    st.rerun()
                else:
                     st.error(f"Reset Failed: {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")

