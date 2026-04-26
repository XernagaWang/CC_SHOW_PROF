import streamlit as st
import pandas as pd
import altair as alt

def render_mission_deepdive(filtered_df: pd.DataFrame, lang: str):
    
    T = {
        "h1": {"English": "🎯 All Missions Overview", "Deutsch": "🎯 Alle Missionen im Überblick"},
        "no_data": {"English": "No data available for analysis.", "Deutsch": "Keine Daten zur Analyse verfügbar."},
        "desc_1": {"English": "Mission Success Rates", "Deutsch": "Mission Erfolgsquoten"},
        "h2": {"English": "🔍 Single Use Case Deep Dive", "Deutsch": "🔍 Detailanalyse eines einzelnen Anwendungsfalls"},
        "no_usecase": {"English": "No Use Case data available.", "Deutsch": "Keine Daten zu Anwendungsfällen verfügbar."},
        "select": {"English": "Select a Use Case to Analyze", "Deutsch": "Wählen Sie einen Anwendungsfall zur Analyse"},
        "banner": {"English": "Analyzing", "Deutsch": "Analyse von"},
        "tests": {"English": "total tests.", "Deutsch": "Tests insgesamt."},
        "rate": {"English": "Success Rate", "Deutsch": "Erfolgsquote"},
        "succ_sessions": {"English": "Successful Sessions", "Deutsch": "Erfolgreiche Sitzungen"},
        "fail_sessions": {"English": "Failed Sessions", "Deutsch": "Fehlgeschlagene Sitzungen"},
        "fail_reasons": {"English": "**Failure Reasons in Use Case**", "Deutsch": "**Fehlerursachen im Anwendungsfall**"},
        "issue_src": {"English": "**Issue Source in Use Case**", "Deutsch": "**Fehlerquelle im Anwendungsfall**"},
        "no_failures": {"English": "No failures!", "Deutsch": "Keine Fehler!"},
        "no_issues": {"English": "No issues!", "Deutsch": "Keine Probleme!"},
        "h3": {"English": "📋 Detailed Records for Use Case:", "Deutsch": "📋 Detaillierte Aufzeichnungen für den Anwendungsfall:"},
        "all_passed": {"English": "All tests passed! No errors to display. 🎉", "Deutsch": "Alle Tests bestanden! Keine Fehler anzuzeigen. 🎉"},
        "vehicle": {"English": "Vehicle", "Deutsch": "Fahrzeug"},
        "infra": {"English": "Infrastructure", "Deutsch": "Infrastruktur"}
    }

    st.subheader(T["h1"][lang])
    
    if filtered_df.empty:
        st.warning(T["no_data"][lang])
        return
        
    st.write(T["desc_1"][lang])
    
    available_missions = sorted(filtered_df['Mission'].dropna().unique().tolist())
    
    if available_missions:
        num_missions = len(available_missions)
        cols = st.columns(num_missions)
        for i, mission_name in enumerate(available_missions):
            mission_subset = filtered_df[filtered_df['Mission'] == mission_name]
            total_mission_tests = len(mission_subset[mission_subset['Status'] == 'Normal Test'])
            success_mission_count = mission_subset[(mission_subset['Status'] == 'Normal Test') & (mission_subset['Success'] == True)].shape[0]
            if total_mission_tests > 0:
                success_rate = (success_mission_count / total_mission_tests) * 100
                cols[i].metric(label=f"{mission_name} ❔", value=f"{success_rate:.1f}%")
            else:
                cols[i].metric(label=f"{mission_name} ❔", value="N/A")
                
    st.markdown("---")
    
    st.subheader(T["h2"][lang])
    
    available_use_cases = sorted(filtered_df['Use Case'].dropna().unique().tolist()) if 'Use Case' in filtered_df.columns else []
    if not available_use_cases:
        st.info(T["no_usecase"][lang])
        return
        
    selected_use_case = st.selectbox(
        T["select"][lang],
        options=available_use_cases
    )
    
    single_mission_df = filtered_df[filtered_df['Use Case'] == selected_use_case]
    total_len = len(single_mission_df)
    
    st.info(f"{T['banner'][lang]} **{selected_use_case}**: {total_len} {T['tests'][lang]}")
    
    valid_single_df = single_mission_df[single_mission_df['Status'] == 'Normal Test']
    total_valid = len(valid_single_df)
    success_count = len(valid_single_df[valid_single_df['Success'] == True])
    failed_count = total_valid - success_count
    success_rate = (success_count / total_valid) * 100 if total_valid > 0 else 0
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric(T["rate"][lang], f"{success_rate:.1f}%")
    kpi_col2.metric(T["succ_sessions"][lang], f"{success_count}")
    kpi_col3.metric(T["fail_sessions"][lang], f"{failed_count}")
    
    st.write("")
    
    col_bar, col_donut = st.columns(2)
    
    with col_bar:
        st.write(T["fail_reasons"][lang])
        failed_protocols_df = single_mission_df[single_mission_df['Root Cause Category'] != 'N/A: Success']
        if not failed_protocols_df.empty:
            cause_counts = failed_protocols_df['Root Cause Category'].value_counts().reset_index()
            cause_counts.columns = ['Root Cause', 'Count']
            
            cause_chart = alt.Chart(cause_counts).mark_bar(color='#5DADE2', cornerRadiusEnd=3).encode(
                x=alt.X('Count:Q', title='Count'),
                y=alt.Y('Root Cause:N', sort='-x', title='', axis=alt.Axis(labelLimit=200)),
                tooltip=['Root Cause', 'Count']
            ).properties(height=250)
            
            st.altair_chart(cause_chart, use_container_width=True)
        else:
            st.success(T["no_failures"][lang])

    with col_donut:
        st.write(T["issue_src"][lang])
        
        site_issues_df = single_mission_df[single_mission_df['Status'] != 'Normal Test']
        total_site_issues = len(site_issues_df)
        
        issue_data = {'Source': [T["vehicle"][lang], T["infra"][lang]], 'Count': [failed_count, total_site_issues]}
        issue_df = pd.DataFrame(issue_data)
        
        if issue_df['Count'].sum() > 0:
            donut_chart = alt.Chart(issue_df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Source", type="nominal", scale=alt.Scale(domain=[T["vehicle"][lang], T["infra"][lang]], range=['#3498DB', '#E74C3C'])),
                tooltip=['Source', 'Count']
            ).properties(height=250)
            st.altair_chart(donut_chart, use_container_width=True)
        else:
            st.success(T["no_issues"][lang])
            
    st.markdown("---")
    
    st.subheader(f"{T['h3'][lang]} {selected_use_case}")
    trouble_df = single_mission_df[
        (single_mission_df['Success'] == False) | 
        (single_mission_df['Status'] != 'Normal Test')
    ]
    
    if not trouble_df.empty:
        cols_to_show = []
        possible_cols = ['Session ID', 'City', 'CPO Name', 'Success', 'Root Cause Category', 'Date']
        for c in possible_cols:
            if c in trouble_df.columns:
                cols_to_show.append(c)
                
        if not cols_to_show:
            cols_to_show = trouble_df.columns.tolist()
            
        st.dataframe(trouble_df[cols_to_show].reset_index(drop=True), use_container_width=True)
    else:
        st.success(T["all_passed"][lang])
