"""
Simple Streamlit UI for Dynamic Tool Registry Management.

Run with: streamlit run ui/tool_registry_admin.py
"""
import streamlit as st
import requests
import json
import os
from datetime import datetime

# Configuration - Use environment variable for Docker, fallback to localhost
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_BASE_URL = BASE_URL + "/admin/registry"
SAP_API_URL = BASE_URL + "/sap/tools"

st.set_page_config(
    page_title="SAP Tool Registry Admin",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ SAP Tool Registry Admin")
st.markdown("Manage SAP tools dynamically without code changes or server restarts")

# Sidebar for stats
st.sidebar.header("📊 Registry Statistics")

try:
    stats = requests.get(f"{API_BASE_URL}/stats").json()
    st.sidebar.metric("Total Tools", stats["total_tools"])
    st.sidebar.metric("Enabled Tools", stats["enabled_tools"])
    st.sidebar.metric("Disabled Tools", stats["disabled_tools"])
    st.sidebar.metric("Registry Version", stats["registry_version"])
    
    if st.sidebar.button("🔄 Reload Registry"):
        response = requests.post(f"{API_BASE_URL}/reload")
        if response.status_code == 200:
            st.sidebar.success("✅ Registry reloaded!")
            st.rerun()
except Exception as e:
    st.sidebar.error(f"❌ Error: {e}")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 List Tools", "➕ Onboard SAP API", "📤 Export/Import", "📊 Tool Details"])

# Tab 1: List Tools
with tab1:
    st.header("Tool Registry")
    
    enabled_only = st.checkbox("Show only enabled tools", value=False)
    
    try:
        url = f"{API_BASE_URL}/tools"
        if enabled_only:
            url += "?enabled_only=true"
        
        tools = requests.get(url).json()
        
        if not tools:
            st.info("No tools found in registry")
        else:
            for tool in tools:
                with st.expander(f"{'✅' if tool['enabled'] else '❌'} {tool['name']}", expanded=False):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Description:** {tool['description']}")
                        st.markdown(f"**Service:** {tool['service_config']['service_name']}")
                        st.markdown(f"**Entity:** {tool['service_config']['entity_name']}")
                        st.markdown(f"**Method:** {tool['service_config']['http_method']}")
                        st.markdown(f"**Version:** {tool['version']}")
                    
                    with col2:
                        if tool['enabled']:
                            if st.button("Disable", key=f"disable_{tool['name']}"):
                                response = requests.post(f"{API_BASE_URL}/tools/{tool['name']}/disable")
                                if response.status_code == 200:
                                    st.success("✅ Disabled!")
                                    st.rerun()
                        else:
                            if st.button("Enable", key=f"enable_{tool['name']}"):
                                response = requests.post(f"{API_BASE_URL}/tools/{tool['name']}/enable")
                                if response.status_code == 200:
                                    st.success("✅ Enabled!")
                                    st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{tool['name']}"):
                            if st.session_state.get(f"confirm_delete_{tool['name']}", False):
                                response = requests.delete(f"{API_BASE_URL}/tools/{tool['name']}")
                                if response.status_code == 204:
                                    st.success("✅ Deleted!")
                                    st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{tool['name']}"] = True
                                st.warning("Click again to confirm deletion")
                    
                    st.json(tool, expanded=False)
    
    except Exception as e:
        st.error(f"❌ Error loading tools: {e}")

# Tab 2: Onboard SAP API
with tab2:
    st.header("Onboard New SAP API")
    st.markdown("Configure a new SAP OData API endpoint for LLM access")
    
    with st.form("create_tool_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            tool_name = st.text_input("Tool Name*", placeholder="get_my_data")
            description = st.text_area("Description*", placeholder="Describe what this tool does...")
            
            st.subheader("Service Configuration")
            service_name = st.text_input("Service Name*", placeholder="ZSD_MY_SERVICE")
            service_namespace = st.text_input("Service Namespace", placeholder="ZSB_MY_SERVICE")
            entity_name = st.text_input("Entity Name*", placeholder="MyEntity")
            odata_version = st.selectbox("OData Version*", ["v4", "v2"], index=0)
            http_method = st.selectbox("HTTP Method*", ["GET", "POST", "PUT", "PATCH", "DELETE"], index=0)
        
        with col2:
            return_direct = st.checkbox(
                "Return Direct to User", 
                value=True,
                help="When checked: Response goes directly to user. When unchecked: Response goes to LLM for processing."
            )
            enabled = st.checkbox("Enabled", value=True)
            
            st.subheader("Defaults (Optional)")
            query_params = st.text_area(
                "Query Parameters (JSON)",
                placeholder='{"select": "field1,field2", "top": "100"}',
                height=100
            )
            
            prompt_hints = st.text_area(
                "Prompt Hints (one per line)",
                placeholder="Filter by date range\nUse specific field names",
                height=100
            )
        
        submitted = st.form_submit_button("🚀 Onboard API")
        
        if submitted:
            # Validate required fields
            if not all([tool_name, description, service_name, entity_name]):
                st.error("❌ Please fill all required fields (marked with *)")
            else:
                try:
                    # Parse optional JSON fields
                    defaults = {}
                    if query_params:
                        try:
                            defaults["query_parameters"] = json.loads(query_params)
                        except:
                            st.error("❌ Invalid JSON in Query Parameters")
                            st.stop()
                    
                    hint_items = []
                    if prompt_hints:
                        hint_items = [h.strip() for h in prompt_hints.split('\n') if h.strip()]
                    
                    # Build tool data
                    tool_data = {
                        "name": tool_name,
                        "description": description,
                        "service_config": {
                            "service_name": service_name,
                            "service_namespace": service_namespace or None,
                            "entity_name": entity_name,
                            "odata_version": odata_version,
                            "http_method": http_method
                        },
                        "return_direct": return_direct,
                        "defaults": defaults,
                        "prompt_hints": {
                            "items": hint_items
                        },
                        "enabled": enabled
                    }
                    
                    # Create tool
                    response = requests.post(f"{API_BASE_URL}/tools", json=tool_data)
                    
                    if response.status_code == 201:
                        st.success(f"✅ API '{tool_name}' onboarded successfully!")
                        st.success("🔄 API is immediately available - no server restart needed!")
                        st.balloons()
                    else:
                        st.error(f"❌ Error: {response.json()['detail']}")
                
                except Exception as e:
                    st.error(f"❌ Error creating tool: {e}")

# Tab 3: Export/Import
with tab3:
    st.header("Backup & Restore")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Export Registry")
        st.markdown("Export the entire registry for backup or migration")
        
        if st.button("📥 Download Registry Backup"):
            try:
                response = requests.get(f"{API_BASE_URL}/export")
                if response.status_code == 200:
                    export_data = response.json()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"tool_registry_export_{timestamp}.json"
                    
                    st.download_button(
                        label="💾 Save JSON File",
                        data=json.dumps(export_data, indent=2),
                        file_name=filename,
                        mime="application/json"
                    )
                    
                    st.success(f"✅ Registry exported successfully!")
                    st.info(f"📊 Exported {len(export_data['tools'])} tools")
            except Exception as e:
                st.error(f"❌ Error exporting: {e}")
    
    with col2:
        st.subheader("📥 Import Registry")
        st.markdown("Import tools from a backup file")
        
        uploaded_file = st.file_uploader("Choose JSON file", type=["json"])
        replace_existing = st.checkbox("Replace existing tools", value=False)
        
        if uploaded_file and st.button("🚀 Import Tools"):
            try:
                import_data = json.load(uploaded_file)
                
                # Post to import endpoint
                response = requests.post(
                    f"{API_BASE_URL}/import",
                    json={
                        "tools": import_data.get("tools", {}),
                        "replace_existing": replace_existing
                    }
                )
                
                if response.status_code == 200:
                    st.success("✅ Tools imported successfully!")
                    st.json(response.json())
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.json()['detail']}")
            
            except Exception as e:
                st.error(f"❌ Error importing: {e}")

# Tab 4: Tool Details
with tab4:
    st.header("Tool Details")
    
    try:
        tools = requests.get(f"{API_BASE_URL}/tools").json()
        tool_names = [t['name'] for t in tools]
        
        selected_tool = st.selectbox("Select Tool", tool_names)
        
        if selected_tool:
            tool_detail = requests.get(f"{API_BASE_URL}/tools/{selected_tool}").json()
            
            st.subheader(f"Details: {selected_tool}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Status", "✅ Enabled" if tool_detail['enabled'] else "❌ Disabled")
                st.metric("Version", tool_detail['version'])
                st.metric("Created", tool_detail['created_at'][:10])
                st.metric("Updated", tool_detail['updated_at'][:10])
                
                # Show return_direct status
                return_direct_val = tool_detail.get('return_direct', False)
                return_direct_label = "🔵 Direct to User" if return_direct_val else "🟢 To LLM"
                return_direct_help = "Response goes directly to user" if return_direct_val else "Response processed by LLM"
                st.metric("Return Mode", return_direct_label, help=return_direct_help)
            
            with col2:
                st.markdown("**Service Configuration:**")
                st.json(tool_detail['service_config'])
            
            st.markdown("**Full Tool Definition:**")
            st.json(tool_detail, expanded=True)
            
            # Update form - Edit complete JSON
            with st.expander("✏️ Edit Tool JSON"):
                with st.form(f"update_tool_{selected_tool}"):
                    st.markdown("**Edit the complete tool configuration as JSON:**")
                    st.markdown("⚠️ Make sure the JSON is valid before updating!")
                    st.info("💡 Note: Read-only fields (name, created_at, updated_at, version) will be automatically removed before updating.")
                    
                    # Convert tool to pretty JSON string for editing
                    tool_json_str = json.dumps(tool_detail, indent=2)
                    
                    new_tool_json = st.text_area(
                        "Tool Configuration (JSON)",
                        value=tool_json_str,
                        height=400,
                        help="Edit the complete JSON structure. Be careful with syntax!"
                    )
                    
                    update_submitted = st.form_submit_button("💾 Update Tool")
                    
                    if update_submitted:
                        try:
                            # Parse and validate JSON
                            update_data = json.loads(new_tool_json)
                            
                            # Remove read-only fields that API doesn't accept
                            read_only_fields = ['name', 'created_at', 'updated_at', 'version']
                            for field in read_only_fields:
                                update_data.pop(field, None)
                            
                            response = requests.put(
                                f"{API_BASE_URL}/tools/{selected_tool}",
                                json=update_data
                            )
                            
                            if response.status_code == 200:
                                st.success("✅ Tool updated successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ Error: {response.json()['detail']}")
                        
                        except json.JSONDecodeError as e:
                            st.error(f"❌ Invalid JSON: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Error updating tool: {e}")
    
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Footer
st.markdown("---")
st.markdown("🛠️ **SAP Tool Registry Admin** | Powered by FastAPI & Streamlit | No code changes required!")
