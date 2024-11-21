import streamlit as st
import altair as alt
import pandas as pd

synth_data = pd.read_csv('streamlit_vis/synth_table_ap_distance_11_21_24.csv')

synth_data['exp_apdist'] = np.exp(synth_data['ap_distance'])
filepaths = [f'https://upconverting.blob.core.windows.net/silica-np-saxs/{uuid}.png' for uuid in synth_data['uuid']] 
synth_data['image'] = filepaths


## TEOS_water chart
chart = alt.Chart(synth_data, width = 600, height = 500).mark_circle(size=100).encode(
    x = 'teos_vol_frac',
    y = 'water_vol_frac',
    color = 'exp_apdist',
    tooltip=['uuid', 'image', 'ap_distance', 'rank', 'campaign', 'water_vol_frac'])

st.title('TEOS_water parameter space')
st.write('Mouse over chart to explore, Not recommended for mobile')
st.altair_chart(chart)


## TEOS_ammonia chart
chart2 = alt.Chart(synth_data, width = 600, height = 500).mark_circle(size=100).encode(
    x = 'teos_vol_frac',
    y = 'ammonia_vol_frac',
    color = 'exp_apdist',
    tooltip=['uuid', 'image', 'ap_distance', 'rank', 'campaign', 'water_vol_frac'])


st.title('TEOS - Ammonia parameter space')
st.altair_chart(chart2)
