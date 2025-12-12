import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

from config import AppConfig
from services.azure_clients import AzureClientManager
from services.document_extractor import DocumentExtractor
from services.contract_analyzer import ContractAnalyzer
from services.service_description_validator import ServiceDescriptionValidator
from ui.styles import Styles
from ui.display_manager import DisplayManager
from utils.excel_writer import convert_validation_to_excel

# Engine that produces legal redline diffs
import legal_redline_diff_engine

def main():
    # Page setup + styles
    AppConfig.setup_page()
    Styles.load()

    # Header
    st.markdown("""
        <div class="header-section">
            <h1>📄 Document Validator System</h1>
            <p>Automated extraction and analysis of contract documents using Azure AI services</p>
        </div>
    """, unsafe_allow_html=True)

    # Validate environment variables early
    if not AppConfig.validate():
        st.stop()

    # Initialize Azure clients
    try:
        azure = AzureClientManager()
        doc_client = getattr(azure, "doc_client", None)
        openai_client = getattr(azure, "openai_client", None)
        if doc_client is None or openai_client is None:
            raise RuntimeError("Azure clients not fully initialized. Check environment variables.")
    except Exception as e:
        st.error("Failed to initialize Azure clients.")
        st.exception(e)
        st.stop()

    extractor = DocumentExtractor(doc_client)
    analyzer = ContractAnalyzer(openai_client)
    service_validator = ServiceDescriptionValidator(openai_client)

    # Sidebar info
    with st.sidebar:
        st.sidebar.markdown(
                '''
                <div style="padding-bottom: 12px;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Allianz.svg/2560px-Allianz.svg.png"
                        width="160" style="padding:5px 0;" />
                </div>
                ''', unsafe_allow_html=True
            )

        st.divider()
        st.header("ℹ️ Application Info")
        st.info("**Document Validator v1.0**\n\nThis application uses Azure Document Intelligence to extract text from PDFs and Azure OpenAI to analyze contract content automatically.")
        st.divider()

    # Session state defaults
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
        st.session_state.result = None
        st.session_state.file_name = None
        st.session_state.extraction_time = 0.0
        st.session_state.analysis_time = 0.0
        st.session_state.page_count = 0
        st.session_state.processing_time = ""

    # File upload
    st.subheader("📤 Upload Document")
    uploaded_file = st.file_uploader("Select a PDF document to analyze", type="pdf")

    if uploaded_file is not None:
        DisplayManager.show_file_info(uploaded_file)

        col1, col2 = st.columns(2)
        with col1:
            process_button = st.button("🚀 Analyze Document", type="primary")
        with col2:
            clear_button = st.button("🔄 Clear Results")

        if clear_button:
            st.session_state.processing_complete = False
            st.session_state.result = None
            st.session_state.file_name = None
            st.experimental_rerun()

        if process_button:
            try:
                # Read PDF bytes
                pdf_content = uploaded_file.read()

                # Extract text
                status = st.empty()
                status.info("📖 Extracting text from PDF...")
                with st.spinner("Extracting text..."):
                    full_text, page_count, extraction_time = extractor.extract_text(pdf_content)
                    service_description_md = extractor.extract_service_description(full_text)
                # debug print left intentionally - remove if not desired
                print(service_description_md)
                st.session_state.extraction_time = extraction_time
                st.session_state.page_count = page_count

                # Analyze contract
                status.info("🔍 Analyzing contract with AI...")
                with st.spinner("Analyzing contract..."):
                    # Step 1: Contract-wide analysis
                    result_json, analysis_time, usage_stats = analyzer.analyze(full_text)

                    # Step 2: Service description validation
                    service_result = service_validator.validate_service_description(service_description_md or "")

                    # ---------------------------------------------------------
                    # START NEW CODE: Run the Legal Redline Diff Engine
                    # ---------------------------------------------------------
                    status.info("⚖️ Running Legal Redline Comparison...")
                    with st.spinner("Running redline comparison..."):
                        redline_results = legal_redline_diff_engine.get_legal_redline_for_document(
                            document_text=full_text
                        ) or {}

                    # OVERWRITE or set the legal_clause_validation key with engine results
                    result_json["legal_clause_validation"] = redline_results
                    # ---------------------------------------------------------
                    # END NEW CODE
                    # ---------------------------------------------------------

                    # Step 3: Append service description result to main JSON
                    result_json["service_description_validation"] = service_result

                # Save stats & session state
                st.session_state.analysis_time = analysis_time
                st.session_state.usage_stats = usage_stats
                st.session_state.processing_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.result = result_json
                st.session_state.file_name = uploaded_file.name
                st.session_state.processing_complete = True

                status.empty()
                st.markdown('<div class="success-box">✅ <b>Document processed successfully!</b></div>', unsafe_allow_html=True)

            except Exception as e:
                st.error("❌ Error Processing Document")
                with st.expander("View Error Details"):
                    st.code(str(e), language="text")

    # Display results if processing complete
    if st.session_state.processing_complete and st.session_state.result:
        DisplayManager.show_processing_stats(
            extraction_time=st.session_state.extraction_time,
            analysis_time=st.session_state.analysis_time,
            page_count=st.session_state.page_count,
            processed_time=st.session_state.processing_time,
            usage_stats=st.session_state.usage_stats
        )
        DisplayManager.show_results(st.session_state.result)

        # Download raw JSON
        json_str = json.dumps(st.session_state.result, indent=2)
        excel_buffer = convert_validation_to_excel(st.session_state.result)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="⬇️ Download Results (JSON)",
                data=json_str,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="⬇️ Download Results (Text)",
                data=json_str,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col3:
            st.download_button(
                label="⬇️ Download Report (Excel)",
                data=excel_buffer,
                file_name=f"contract_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    # Footer
    st.divider()
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    with footer_col1:
        st.caption("📝 Contract Analyzer v1.0")
    with footer_col2:
        st.caption(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with footer_col3:
        st.caption("🔒 Enterprise Grade | Production Ready")

if __name__ == "__main__":
    main()
