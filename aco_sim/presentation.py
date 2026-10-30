"""Shared dashboard styling and charts. No changes to simulation calculations."""
from html import escape
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

TEAL = '#147D73'
BLUE = '#4567A6'
AMBER = '#A76516'
INK = '#213D44'
MUTED = '#60767D'
GRID = '#E6ECEC'


def style():
    st.markdown('''<style>
    .stApp {background:#F7F9FA; color:#213D44;}
    .block-container {padding-top:2.4rem; padding-bottom:3rem; max-width:1600px;}
    [data-testid="stSidebar"] {background:#EDF2F3; border-right:1px solid #DCE5E6;}
    [data-testid="stSidebar"] .block-container {padding-top:1.5rem;}
    h1 {font-size:2rem !important; letter-spacing:-.035em; font-weight:720 !important;}
    h2 {font-size:1.4rem !important; letter-spacing:-.025em; padding-top:.4rem !important;}
    h3 {font-size:1.08rem !important;}
    [data-testid="stMetric"] {background:white; border:1px solid #DFE7E8;
      border-top:3px solid #147D73; border-radius:12px; padding:14px 18px; min-height:104px;}
    [data-testid="stMetricValue"] {font-size:1.85rem; font-weight:650; letter-spacing:-.035em;}
    [data-testid="stMetricLabel"] {color:#526B73; font-size:.8rem;}
    [data-testid="stPlotlyChart"] {background:white; border:1px solid #E1E8E9; border-radius:12px; overflow:hidden;}
    [data-testid="stDataFrame"] {border-radius:10px; overflow:hidden;}
    [data-testid="stExpander"] {background:#FFFFFF; border-radius:10px;}
    [data-baseweb="tab-list"] {gap:1.2rem; border-bottom:1px solid #DBE4E5;}
    [data-baseweb="tab"] {padding:10px 1px; font-weight:600;}
    [data-testid="stAlert"] {border-radius:10px; font-size:.88rem;}
    .brand {background:#153E43; color:#fff; padding:20px; border-radius:14px; margin:0 0 18px;}
    .brand small {color:#BFDAD7; letter-spacing:.13em; font-size:10px;}
    .brand strong {display:block; font-size:23px; line-height:1.25; margin:8px 0;}
    .brand span {font-size:12px; color:#D3E6E4;}
    .context {display:flex; flex-wrap:wrap; gap:8px; margin:0 0 14px;}
    .context span {background:#E6F1EF; border:1px solid #C8DFD9; color:#245D55;
      border-radius:20px; padding:5px 11px; font-size:12px; font-weight:600;}
    .context .assumption {background:#FFF2DE; color:#82500C; border-color:#E9D4B1;}
    .section-note {color:#60767D; font-size:13px; margin:0 0 12px;}
    @media (max-width:700px) {
      .block-container {padding:1.5rem 1rem;}
      h1 {font-size:1.6rem !important;}
      [data-testid="stMetricValue"] {font-size:1.5rem;}
      [data-baseweb="tab-list"] {gap:.65rem;}
    }
    </style>''', unsafe_allow_html=True)


def context(mode, count, years):
    label = {'Published cluster evidence':'Published evidence · 2024 baseline',
             'Existing project simulation':'Synthetic scenario · unvalidated',
             'Import annual CSVs':'Your imported records'}.get(mode, mode)
    css = 'assumption' if mode == 'Existing project simulation' else ''
    st.markdown(f'<div class="context"><span class="{css}">{escape(label)}</span>'
                f'<span>{count} clusters selected</span><span>Planning {years[0]}–{years[-1]}</span></div>',
                unsafe_allow_html=True)


def base(fig, height=500):
    fig.update_layout(template='plotly_white',height=height,
        paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial, sans-serif',size=12,color=INK),
        margin=dict(l=12,r=40,t=32,b=48),hoverlabel=dict(bgcolor='white',font_size=13),
        legend=dict(orientation='h',y=1.13,x=0,title_text=''))
    fig.update_xaxes(gridcolor=GRID,zeroline=False,title_font_size=11)
    fig.update_yaxes(gridcolor=GRID,zeroline=False,title_font_size=11,automargin=True)
    return fig


def short(name):
    return name.replace(' Health Cluster','')


def ranked_figure(data, metric, unit, color=TEAL):
    valid=data.dropna(subset=['value']).sort_values(['value','cluster_name'])
    fig=go.Figure(go.Bar(x=valid.value.tolist(),y=valid.cluster_name.map(short).tolist(),orientation='h',
        marker_color=color,text=valid.value.tolist(),texttemplate='%{text:,.0f}',textposition='outside',
        cliponaxis=False,customdata=valid[['cluster_name']].to_numpy(),
        hovertemplate='<b>%{customdata[0]}</b><br>%{x:,.0f} '+escape(unit)+'<extra></extra>'))
    base(fig,max(270,26*len(valid)+80))
    fig.update_layout(showlegend=False,bargap=.26)
    max_value=valid.value.max() if len(valid) else 0
    fig.update_xaxes(title_text=unit,rangemode='tozero',range=[0,max_value*1.23 if max_value else 1],tickformat='~s')
    fig.update_yaxes(title_text='',showgrid=False)
    return fig


def ranking(data, metric, unit, key, color=TEAL):
    if data.value.notna().any():
        st.plotly_chart(ranked_figure(data,metric,unit,color),use_container_width=True,
                        config={'displaylogo':False,'scrollZoom':False},key=key)
    else:
        st.info('No reported values for this selection. Missing observations cannot be ranked.')
    missing=data.loc[data.value.isna(),'cluster_name'].map(short).tolist()
    if missing:
        st.caption('Not ranked — source value unavailable: '+', '.join(missing)+'.')


def source_figure(data):
    data=data.sort_values('value_2024')
    fig=go.Figure()
    for field,label,color in [('value_2024','MoH · 2024',TEAL),('value_undated','HHC · year unspecified',AMBER)]:
        fig.add_trace(go.Bar(x=data[field].tolist(),y=data.cluster_name.map(short).tolist(),orientation='h',
            name=label,marker_color=color,customdata=data[['cluster_name']].to_numpy(),
            hovertemplate='<b>%{customdata[0]}</b><br>%{x:,.0f} beds<extra>'+label+'</extra>'))
    base(fig,max(350,len(data)*40+100))
    fig.update_layout(barmode='group',bargap=.25)
    fig.update_xaxes(title_text='Reported beds · separate source snapshots',rangemode='tozero',tickformat=',')
    fig.update_yaxes(showgrid=False)
    return fig


def coverage_figure(inventory):
    labels=['Pathways','Related public<br>indicators','Synthetic<br>profile','Coded<br>activity','IPU capacity<br>allocation']
    rows=[]
    for row in inventory.itertuples():
        related=not row.related_indicators.startswith('No sufficiently')
        modeled=row.legacy_model.startswith('Synthetic profile')
        rows.append([2,1 if related else 0,1 if modeled else 0,0,0])
    z=np.array(rows)
    text=np.array([['Defined','Context' if r[1] else 'Missing','Synthetic' if r[2] else 'Missing','Missing','Missing'] for r in rows])
    names=inventory.ipu.str.replace('Population Health, Screening and Immunisation','Population health / screening',regex=False)
    names=names.str.replace('Acute Medicine and Same-Day Emergency Care','Acute medicine / SDEC',regex=False)
    fig=go.Figure(go.Heatmap(z=z.tolist(),x=labels,y=names.tolist(),text=text.tolist(),
        texttemplate='%{text}',textfont=dict(size=11),xgap=4,ygap=4,zmin=0,zmax=2,
        colorscale=[[0,'#EDF0F2'],[.249,'#EDF0F2'],[.25,'#F6DEB3'],[.749,'#F6DEB3'],[.75,'#C5E5DE'],[1,'#C5E5DE']],
        showscale=False,hovertemplate='<b>%{y}</b><br>%{x}: %{text}<extra></extra>'))
    base(fig,max(280,len(inventory)*30+100))
    fig.update_yaxes(autorange='reversed',showgrid=False)
    fig.update_xaxes(side='top',showgrid=False,tickfont_size=11)
    fig.update_layout(margin=dict(l=10,r=10,t=70,b=15))
    return fig


def trend_figure(matrix, unit):
    fig=go.Figure()
    for name,row in matrix.iterrows():
        fig.add_trace(go.Scatter(x=matrix.columns.tolist(),y=[None if pd.isna(v) else float(v) for v in row],
            name=short(name),mode='lines+markers' if len(row)<3 else 'lines',connectgaps=False,
            hovertemplate='%{x}: %{y:,.1f}<extra>'+escape(short(name))+'</extra>'))
    base(fig,420)
    fig.update_layout(legend=dict(orientation='v',x=1.02,y=1),colorway=[TEAL,BLUE,AMBER,'#8774A2','#527D96','#8F635C'])
    fig.update_xaxes(title_text='Year',dtick=5 if len(matrix.columns)>10 else 1,tickformat='d')
    fig.update_yaxes(title_text=unit,rangemode='tozero')
    return fig
