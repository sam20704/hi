        # ... inside show_results(result) ...

        # Legal Clause Validation
        with st.expander("⚖️ Legal Clause Validation", expanded=True):
            legal_data = result.get("legal_clause_validation", {})

            if not legal_data:
                st.info("No legal clause validation data available.")
            elif "changes" in legal_data:
                # Fallback for old data
                st.warning("Legacy data format detected.")
                st.json(legal_data)
            else:
                found_valid_section = False
                for section_name, section_data in legal_data.items():
                    if not isinstance(section_data, dict):
                        continue
                    
                    found_valid_section = True
                    status = section_data.get("status", "UNKNOWN")
                    diff_html = section_data.get("diff_markdown", "")
                    change_ratio = section_data.get("change_ratio", 0.0)

                    # Header
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"#### {section_name}")
                    with col2:
                        st.markdown(f"**Status:** <span class='{get_status_style(status)}'>{status}</span>", 
                                    unsafe_allow_html=True)

                    # Body
                    if status == "MATCH":
                        st.success("✅ Exact match with Knowledge Base.")
                    elif status == "CHANGED":
                        st.warning(f"⚠️ Deviation detected ({change_ratio:.1%} change)")
                        if diff_html:
                            st.caption("Redline Difference:")
                            st.markdown(
                                f"""<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #ddd; font-family: monospace; white-space: pre-wrap;">{diff_html}</div>""", 
                                unsafe_allow_html=True
                            )
                        else:
                            st.write("Differences found, but no visual redline available.")
                    
                    st.divider()

                if not found_valid_section:
                    st.write("No valid section comparisons found.")
