import streamlit as st
import altair as alt
import pandas as pd

TOTAL_NATIONAL_CPOS = 361 

def render_national_overview(filtered_df: pd.DataFrame, lang: str):
    
    T = {
        "h1": {"English": "🇨🇳 National Test Progress & Coverage (Core KPIs)", "Deutsch": "🇨🇳 Nationaler Testfortschritt & Abdeckung (Kern-KPIs)"},
        "no_data": {"English": "No test data found. Please check filters or source data.", "Deutsch": "Keine Testdaten gefunden. Bitte überprüfen Sie Filter oder Quelldaten."},
        "hero_title_1": {"English": "🗂️ Overall Mission Effort", "Deutsch": "🗂️ Gesamtaufwand der Mission"},
        "hero_title_2": {"English": "⚡ Charging Performance (Normal Tests Only)", "Deutsch": "⚡ Ladeleistung (Nur normale Tests)"},
        "metric_tests": {"English": "Total Test Records", "Deutsch": "Gesamte Testaufzeichnungen"},
        "metric_test_help": {"English": "Includes all successful, failed, and hardware-damaged visits", "Deutsch": "Enthält alle erfolgreichen, fehlgeschlagenen und durch Hardware beschädigten Besuche"},
        "metric_cpo": {"English": "CPOs Tested", "Deutsch": "Getestete CPOs"},
        "metric_cpo_help": {"English": "Total number of operators tested", "Deutsch": "Gesamtanzahl der getesteten Betreiber"},
        "metric_site": {"English": "Site/Access Issues", "Deutsch": "Standort-/Zugangsprobleme"},
        "metric_site_help": {"English": "Visits where testing was impossible due to physical/hardware issues at site", "Deutsch": "Besuche, bei denen das Testen aufgrund physischer/hardwarebedingter Probleme unmöglich war"},
        "metric_valid": {"English": "Valid Test Sessions", "Deutsch": "Gültige Testsitzungen"},
        "metric_valid_help": {"English": "Tests where charger could be plugged in and protocol testing began", "Deutsch": "Tests, bei denen Stecker eingesteckt werden konnte und der Protokolltest begann"},
        "metric_success": {"English": "Charging Success Rate", "Deutsch": "Ladeerfolgsquote"},
        "metric_success_help": {"English": "True success rate among valid tests", "Deutsch": "Wahre Erfolgsquote bei gültigen Tests"},
        "metric_explore": {"English": "National CPO Exploration", "Deutsch": "Nationale CPO-Erkundung"},
        "metric_explore_help": {"English": "Progress in covering all national CPOs", "Deutsch": "Fortschritt bei der Abdeckung aller nationalen CPOs"},
        "h2": {"English": "📊 Issue Distribution (The Blame Game)", "Deutsch": "📊 Fehlerverteilung"},
        "h2_donut": {"English": "**Overall Record Status**", "Deutsch": "**Status der Aufzeichnungen gesamt**"},
        "h2_bar": {"English": "**Top 5 Root Causes**", "Deutsch": "**Die 5 häufigsten Fehlerursachen**"},
        "donut_cat": {"English": "Category", "Deutsch": "Kategorie"},
        "donut_passed": {"English": "Passed", "Deutsch": "Bestanden"},
        "donut_protocol": {"English": "Protocol/Vehicle Issues", "Deutsch": "Protokoll-/Fahrzeugprobleme"},
        "donut_infrastructure": {"English": "Site/Infrastructure Issues", "Deutsch": "Standort-/Infrastrukturprobleme"},
        "no_error": {"English": "Perfect! No failed records found.", "Deutsch": "Perfekt! Keine fehlerhaften Datensätze gefunden."},
        "bar_count": {"English": "Count", "Deutsch": "Anzahl"},
        "bar_cause": {"English": "Root Cause", "Deutsch": "Fehlerursache"},
        "bar_prop": {"English": "Proportion", "Deutsch": "Anteil"},
        "h3": {"English": "🚗 Vehicle & Software Performance", "Deutsch": "🚗 Fahrzeug- & Softwareleistung"},
        "h3_vin": {"English": "**Success/Failure by Vehicle Model**", "Deutsch": "**Erfolg/Misserfolg nach Fahrzeugmodell**"},
        "h3_sw": {"English": "**Success/Failure by Software Version**", "Deutsch": "**Erfolg/Misserfolg nach Softwareversion**"},
        "no_vin": {"English": "No vehicle data available.", "Deutsch": "Keine Fahrzeugdaten verfügbar."},
        "no_sw": {"English": "No software data available.", "Deutsch": "Keine Softwaredaten verfügbar."},
        "h4": {"English": "🗺️ Macroscopic Geographic Performance", "Deutsch": "🗺️ Makroskopische geografische Leistung"},
        "h4_city": {"English": "**Success Rate by City**", "Deutsch": "**Erfolgsquote nach Stadt**"},
        "h4_cpo": {"English": "**Top 5 CPOs with Most Failures**", "Deutsch": "**Die 5 CPOs mit den meisten Fehlern**"},
        "test_count": {"English": "Total Tests", "Deutsch": "Tests insgesamt"},
        "fail_count": {"English": "Failures", "Deutsch": "Fehler"}
    }

    st.subheader(T["h1"][lang])
    
    if filtered_df.empty:
        st.warning(T["no_data"][lang])
        return
        
    valid_tests_df = filtered_df[filtered_df['Status'] == 'Normal Test'].copy()
    site_issues_df = filtered_df[filtered_df['Status'] != 'Normal Test'].copy()

    # --- Metrics Calculation ---
    total_charges = len(filtered_df)
    unique_stations_tested = filtered_df['Station Name'].nunique() if 'Station Name' in filtered_df.columns else 0
    unique_cpos_tested = filtered_df['CPO Name'].nunique() if 'CPO Name' in filtered_df.columns else 0

    total_valid_tests = len(valid_tests_df)
    success_count = valid_tests_df['Success'].sum() if not valid_tests_df.empty else 0
    failure_count = total_valid_tests - success_count
    
    success_rate = (success_count / total_valid_tests) * 100 if total_valid_tests > 0 else 0
    site_issue_rate = (len(site_issues_df) / total_charges) * 100 if total_charges > 0 else 0
    
    # Custom CSS
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] {
            color: #E6E6E6; 
        }
        h4 {
            color: #0066B1; 
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown(f"#### {T['hero_title_1'][lang]}")
    kpi_cols_1 = st.columns(3)
    kpi_cols_1[0].metric(T["metric_tests"][lang], f"{total_charges:,}", help=T["metric_test_help"][lang])
    kpi_cols_1[1].metric(T["metric_cpo"][lang], f"{unique_cpos_tested}", help=T["metric_cpo_help"][lang])
    kpi_cols_1[2].metric(T["metric_site"][lang], f"{len(site_issues_df)}", help=T["metric_site_help"][lang])

    st.write("") 

    st.markdown(f"#### {T['hero_title_2'][lang]}")
    kpi_cols_2 = st.columns(3)
    kpi_cols_2[0].metric(T["metric_valid"][lang], f"{total_valid_tests:,}", help=T["metric_valid_help"][lang])
    kpi_cols_2[1].metric(T["metric_success"][lang], f"{success_rate:.1f}%", help=T["metric_success_help"][lang])
    
    cpo_coverage_pct = (unique_cpos_tested / TOTAL_NATIONAL_CPOS) * 100 if TOTAL_NATIONAL_CPOS > 0 else 0
    kpi_cols_2[2].metric(
        T["metric_explore"][lang], 
        f"{unique_cpos_tested} / {TOTAL_NATIONAL_CPOS}", 
        f"{cpo_coverage_pct:.1f}%",
        help=T["metric_explore_help"][lang]
    )

    st.markdown("---")

    # Issue Distribution Donut Chart
    st.subheader(T["h2"][lang])
    col_donut, col_bar = st.columns([1, 1.5])
    
    with col_donut:
        st.write(T["h2_donut"][lang])
        donut_data = pd.DataFrame({
            'Category': [T["donut_passed"][lang], T["donut_protocol"][lang], T["donut_infrastructure"][lang]],
            'Count': [success_count, failure_count, len(site_issues_df)]
        })
        donut_chart = alt.Chart(donut_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(field="Category", type="nominal", 
                            scale=alt.Scale(domain=[T["donut_passed"][lang], T["donut_protocol"][lang], T["donut_infrastructure"][lang]],
                                            range=['#00A36C', '#E32636', '#F39C12']), 
                            legend=alt.Legend(title=T["donut_cat"][lang], orient='bottom')),
            tooltip=['Category', 'Count']
        ).properties(height=250)
        st.altair_chart(donut_chart, use_container_width=True)

    with col_bar:
        st.write(T["h2_bar"][lang])
        failed_all_df = filtered_df[~( (filtered_df['Status'] == 'Normal Test') & (filtered_df['Success'] == True) )]
        
        if failed_all_df.empty:
            st.success(T["no_error"][lang])
        else:
            root_cause_counts = failed_all_df['Root Cause Category'].value_counts().nlargest(5).reset_index()
            root_cause_counts.columns = ['Root Cause', 'Count']
            
            bar_chart = alt.Chart(root_cause_counts).mark_bar(color='#E32636', cornerRadiusEnd=3).encode(
                x=alt.X('Count:Q', title=T["bar_count"][lang]),
                y=alt.Y('Root Cause:N', title='', sort='-x'),
                tooltip=['Root Cause', 'Count']
            ).properties(height=240) 
            st.altair_chart(bar_chart, use_container_width=True)

    if 'MODEL' in valid_tests_df.columns:
        ac_df = valid_tests_df[valid_tests_df['MODEL'] == 'AC']
        dc_df = valid_tests_df[valid_tests_df['MODEL'] == 'DC']
        
        ac_dc_df = valid_tests_df[valid_tests_df['MODEL'].isin(['AC', 'DC'])].copy()
        if not ac_dc_df.empty:
            ac_dc_counts = ac_dc_df.groupby(['MODEL', 'Success']).size().reset_index(name='Count')
            ac_dc_chart = alt.Chart(ac_dc_counts).mark_bar(cornerRadiusEnd=3).encode(
                y=alt.Y('MODEL:N', title='', sort='-x'),
                x=alt.X('Count:Q', title=T["bar_prop"][lang], stack='normalize', axis=alt.Axis(format='%')),
                color=alt.Color('Success:N', 
                                scale=alt.Scale(domain=[True, False], range=['#00A36C', '#E32636']),
                                legend=None), 
                tooltip=['MODEL', 'Success', 'Count']
            ).properties(height=240)
            st.altair_chart(ac_dc_chart, use_container_width=True)
            
            ac_rate = ac_df['Success'].mean() * 100 if len(ac_df) > 0 else 0
            dc_rate = dc_df['Success'].mean() * 100 if len(dc_df) > 0 else 0
            st.caption(f"**AC**: {ac_rate:.1f}% ({len(ac_df)} Tests) &nbsp;&nbsp;|&nbsp;&nbsp; **DC**: {dc_rate:.1f}% ({len(dc_df)} Tests)")

    st.markdown("---")

    # Vehicle & Software Performance
    st.subheader(T["h3"][lang])
    col_vin, col_sw = st.columns(2)
    
    sw_col = 'SW Version' if 'SW Version' in valid_tests_df.columns else ('Software Version' if 'Software Version' in valid_tests_df.columns else None)
    vin_col = 'VIN' if 'VIN' in valid_tests_df.columns else ('Vehicle Model' if 'Vehicle Model' in valid_tests_df.columns else None)
    
    with col_vin:
        st.write(T["h3_vin"][lang])
        if vin_col and not valid_tests_df.empty:
            vin_counts = valid_tests_df.groupby([vin_col, 'Success']).size().reset_index(name='Count')
            if not vin_counts.empty:
                vin_chart = alt.Chart(vin_counts).mark_bar(cornerRadiusEnd=3).encode(
                    y=alt.Y(f'{vin_col}:N', title='Vehicle', sort='-x'),
                    x=alt.X('Count:Q', title='Tests', stack='zero'),
                    color=alt.Color('Success:N', 
                                    scale=alt.Scale(domain=[True, False], range=['#00A36C', '#E32636'])),
                    tooltip=[vin_col, 'Success', 'Count']
                ).properties(height=250)
                st.altair_chart(vin_chart, use_container_width=True)
            else:
                st.info(T["no_vin"][lang])
        else:
            st.info(T["no_vin"][lang])

    with col_sw:
        st.write(T["h3_sw"][lang])
        if sw_col and not valid_tests_df.empty:
            sw_counts = valid_tests_df.groupby([sw_col, 'Success']).size().reset_index(name='Count')
            if not sw_counts.empty:
                sw_chart = alt.Chart(sw_counts).mark_bar(cornerRadiusEnd=3).encode(
                    y=alt.Y(f'{sw_col}:N', title='Software', sort='-x'),
                    x=alt.X('Count:Q', title='Tests', stack='zero'),
                    color=alt.Color('Success:N', 
                                    scale=alt.Scale(domain=[True, False], range=['#00A36C', '#E32636']),
                                    legend=None), 
                    tooltip=[sw_col, 'Success', 'Count']
                ).properties(height=250)
                st.altair_chart(sw_chart, use_container_width=True)
            else:
                st.info(T["no_sw"][lang])
        else:
            st.info(T["no_sw"][lang])

    st.markdown("---")

    # City Performance
    st.subheader(T["h4"][lang])
    col4_left, col4_right = st.columns([1, 1])
    
    with col4_left:
        st.write(T["h4_city"][lang])
        if 'City' in valid_tests_df.columns and not valid_tests_df.empty:
            city_success = valid_tests_df.groupby('City')['Success'].mean().reset_index()
            city_success['Success Rate'] = city_success['Success'] * 100
            
            city_chart = alt.Chart(city_success).mark_bar(color='#5DADE2', cornerRadiusEnd=3).encode(
                x=alt.X('Success Rate:Q', title='Success Rate (%)', scale=alt.Scale(domain=[0, 100])),
                y=alt.Y('City:N', title='', sort='-x'),
                tooltip=['City', alt.Tooltip('Success Rate:Q', format='.1f')]
            ).properties(height=250)
            st.altair_chart(city_chart, use_container_width=True)

    with col4_right:
        st.write(T["h4_cpo"][lang])
        if 'CPO Name' in valid_tests_df.columns and not valid_tests_df.empty:
            valid_tests_df_tmp = valid_tests_df.copy()
            valid_tests_df_tmp['Failures'] = ~valid_tests_df_tmp['Success']
            
            cpo_success = valid_tests_df_tmp.groupby('CPO Name').agg(
                Success_Rate=('Success', 'mean'),
                Test_Count=('Success', 'count'),
                Fail_Count=('Failures', 'sum')
            ).reset_index()
            cpo_success['Success_Rate'] = cpo_success['Success_Rate'] * 100
            
            worst_cpos = cpo_success.nlargest(5, 'Fail_Count').sort_values('Fail_Count', ascending=False)
            
            cpo_chart = alt.Chart(worst_cpos).mark_bar(color='#E32636', cornerRadiusEnd=3).encode(
                x=alt.X('Fail_Count:Q', title=T["fail_count"][lang]),
                y=alt.Y('CPO Name:N', title='', sort='-x'),
                tooltip=['CPO Name', alt.Tooltip('Fail_Count:Q', title=T["fail_count"][lang]), 
                         alt.Tooltip('Success_Rate:Q', format='.1f'), 
                         alt.Tooltip('Test_Count:Q', title=T["test_count"][lang])]
            ).properties(height=250)
            st.altair_chart(cpo_chart, use_container_width=True)

