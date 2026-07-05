"""
dashboard/app.py — RPPI Maroc Professional Dashboard
Run: streamlit run dashboard/app.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime

from database.models import SessionLocal, CleanListing, PriceIndex
from config.settings import CITIES, DASHBOARD_TITLE, PROJECT

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Observatoire Immobilier — Maroc",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
/* Global font and background */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * {
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #64748b !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}

/* KPI cards */
.kpi-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 4px;
    line-height: 1.2;
}
.kpi-label {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
}
.kpi-delta {
    font-size: 12px;
    color: #22c55e;
    margin-top: 4px;
}

/* Section headers */
.section-header {
    font-size: 13px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e293b;
}

/* Source badge */
.source-badge {
    display: inline-block;
    background: #172554;
    color: #93c5fd;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #1d4ed8;
    margin-right: 6px;
}

/* City pill */
.city-pill {
    display: inline-block;
    background: #134e4a;
    color: #5eead4;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 12px;
    margin: 2px;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    background: #0f172a;
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
    background: #1e293b !important;
    color: #f1f5f9 !important;
}

/* Metric override */
[data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #f1f5f9 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e293b !important;
    border-radius: 8px;
}

/* Divider */
hr {
    border-color: #1e293b !important;
    margin: 16px 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Dark plotly theme ─────────────────────────────────────
PLOTLY_THEME = dict(
    plot_bgcolor  = "#0f172a",
    paper_bgcolor = "#0f172a",
    font_color    = "#94a3b8",
    font_size     = 12,
    xaxis         = dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    yaxis         = dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    margin        = dict(l=16, r=16, t=40, b=16),
)
COLORS = ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899"]

# ── Data loaders ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_listings():
    session = SessionLocal()
    rows = session.query(CleanListing).all()
    session.close()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        "city": r.city, "region": r.region, "neighborhood": r.neighborhood,
        "transaction": r.transaction, "property_type": r.property_type,
        "price": r.price, "surface": r.surface,
        "price_per_m2": r.price_per_m2, "log_price": r.log_price,
        "rooms": r.rooms, "year_quarter": r.year_quarter,
        "year": r.year, "month": r.month,
        "latitude": r.latitude, "longitude": r.longitude,
        "quality_score": r.quality_score, "scraped_at": r.scraped_at,
        "source": r.source,
    } for r in rows])

@st.cache_data(ttl=3600)
def load_index():
    session = SessionLocal()
    rows = session.query(PriceIndex).all()
    session.close()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        "year_quarter": r.year_quarter, "city": r.city,
        "transaction": r.transaction, "property_type": r.property_type,
        "index_value": r.index_value, "median_price": r.median_price,
        "avg_price_m2": r.avg_price_m2, "listing_count": r.listing_count,
    } for r in rows])

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 20px 0 16px; text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">🏠</div>
        <div style="font-size: 15px; font-weight: 700; color: #f1f5f9;">Observatoire Immobilier</div>
        <div style="font-size: 11px; color: #475569; margin-top: 4px;">Maroc · RPPI Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    df_all = load_listings()
    cities_avail = sorted(df_all["city"].dropna().unique()) if not df_all.empty else []

    st.markdown('<div class="section-header">Filtres</div>', unsafe_allow_html=True)
    sel_cities = st.multiselect("Villes", cities_avail, default=cities_avail,
                                 label_visibility="collapsed",
                                 placeholder="Toutes les villes")
    sel_txn    = st.selectbox("Transaction", ["Tous","location","vente"],
                               label_visibility="collapsed")
    sel_type   = st.multiselect("Type de bien",
        ["appartement","villa","studio","riad","duplex","autre"],
        default=["appartement","villa","studio"],
        label_visibility="collapsed",
        placeholder="Tous les types")
    sources_avail = sorted(df_all["source"].dropna().unique()) if not df_all.empty else []
    sel_source = st.multiselect("Source", sources_avail, default=sources_avail,
                                 label_visibility="collapsed",
                                 placeholder="Toutes les sources")

    st.divider()

    # Mini stats in sidebar
    if not df_all.empty:
        total = len(df_all)
        cities_n = df_all["city"].nunique()
        src_counts = df_all["source"].value_counts()
        src_rows = "".join(f"""
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-size: 12px; color: #64748b;">{s.capitalize()}</span>
                <span style="font-size: 12px; font-weight: 600; color: #3b82f6;">{n:,}</span>
            </div>""" for s, n in src_counts.items())
        st.markdown(f"""
        <div style="padding: 8px 0;">
            <div style="font-size: 11px; color: #475569; text-transform: uppercase;
                        letter-spacing: 0.06em; margin-bottom: 10px;">Base de données</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 12px; color: #64748b;">Annonces</span>
                <span style="font-size: 12px; font-weight: 600; color: #f1f5f9;">{total:,}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-size: 12px; color: #64748b;">Villes</span>
                <span style="font-size: 12px; font-weight: 600; color: #f1f5f9;">{cities_n}</span>
            </div>
            {src_rows}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"""
    <div style="font-size: 10px; color: #334155; line-height: 1.8;">
        v{PROJECT['version']} · {PROJECT['type']}<br>
        Méthode: {PROJECT['methodology']}<br>
        Base: {PROJECT.get('base_period','2024-Q1')} = 100<br>
        Réf: IMF RPPI Handbook 2013
    </div>
    """, unsafe_allow_html=True)

# ── Filter ─────────────────────────────────────────────────
def filt(df):
    if df.empty: return df
    if sel_cities:
        df = df[df["city"].isin(sel_cities)]
    if sel_txn != "Tous":
        df = df[df["transaction"] == sel_txn]
    if sel_type:
        df = df[df["property_type"].isin(sel_type)]
    if sel_source:
        df = df[df["source"].isin(sel_source)]
    return df

df = filt(df_all)

# ── Header ─────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="padding: 8px 0 4px;">
        <h1 style="font-size: 24px; font-weight: 700; margin: 0; color: #f1f5f9;">
            Observatoire des Prix Immobiliers
        </h1>
        <p style="font-size: 13px; color: #475569; margin: 4px 0 0;">
            Indice Hédonique des Prix Résidentiels (RPPI) · Maroc · Statistiques expérimentales
        </p>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    badge_html = "".join(f'<span class="source-badge">{s.capitalize()}</span> '
                          for s in sources_avail) or '<span class="source-badge">—</span>'
    st.markdown(f"""
    <div style="text-align: right; padding-top: 8px;">
        <div style="font-size: 11px; color: #475569;">Dernière collecte</div>
        <div style="font-size: 13px; font-weight: 600; color: #f1f5f9;">
            {datetime.today().strftime('%d %b %Y')}
        </div>
        <div style="margin-top: 4px;">
            {badge_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Tabs ───────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "  Vue d'ensemble  ",
    "  Indice RPPI  ",
    "  Analyse EDA  ",
    "  Carte spatiale  ",
    "  Données  ",
    "  Méthodologie  ",
    "  Sources  ",
])

# ══ TAB 1 — OVERVIEW ══════════════════════════════════════
with t1:
    if df.empty:
        st.warning("Aucune donnée. Lancez: `python main.py --ingest` puis `--clean`")
    else:
        rent_df = df[df["transaction"]=="location"]["price"].dropna()
        sale_df = df[df["transaction"]=="vente"]["price"].dropna()
        ppm2_df = df["price_per_m2"].dropna()

        # KPI row
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{len(df):,}</div>
                <div class="kpi-label">Annonces analysées</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            val = f"{rent_df.median():,.0f} DH" if len(rent_df) else "N/A"
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:#3b82f6">{val}</div>
                <div class="kpi-label">Loyer médian / mois</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            val = f"{sale_df.median()/1e6:.2f} MDH" if len(sale_df) else "N/A"
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:#10b981">{val}</div>
                <div class="kpi-label">Prix vente médian</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            val = f"{ppm2_df.median():,.0f} DH" if len(ppm2_df) else "N/A"
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:#f59e0b">{val}</div>
                <div class="kpi-label">Prix médian / m²</div>
            </div>""", unsafe_allow_html=True)
        with c5:
            qs = df["quality_score"].mean()
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:#8b5cf6">{qs:.0%}</div>
                <div class="kpi-label">Score qualité moyen</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b = st.columns([3, 2])
        with col_a:
            st.markdown('<div class="section-header">Prix médian par ville et transaction</div>',
                        unsafe_allow_html=True)
            cp = (df.groupby(["city","transaction"])["price"]
                  .median().reset_index().sort_values("price"))
            fig = px.bar(cp, x="price", y="city", color="transaction",
                         orientation="h", barmode="group",
                         color_discrete_map={"location":"#3b82f6","vente":"#10b981"},
                         labels={"price":"Prix médian (DH)","city":""})
            fig.update_layout(**PLOTLY_THEME, height=320,
                              legend=dict(orientation="h", yanchor="bottom",
                                          y=1.02, x=0, font_color="#94a3b8"))
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown('<div class="section-header">Répartition par type de bien</div>',
                        unsafe_allow_html=True)
            tc = df["property_type"].value_counts().reset_index()
            tc.columns = ["type","count"]
            fig2 = px.pie(tc, names="type", values="count",
                          color_discrete_sequence=COLORS, hole=0.55)
            fig2.update_layout(**PLOTLY_THEME, height=320,
                               legend=dict(font_color="#94a3b8"))
            fig2.update_traces(textfont_color="#f1f5f9", marker_line_width=0)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-header">Distribution des prix au m² par ville</div>',
                    unsafe_allow_html=True)
        box_df = df.dropna(subset=["price_per_m2"])
        fig3 = px.violin(box_df, x="city", y="price_per_m2",
                          color="transaction", box=True,
                          color_discrete_map={"location":"#3b82f6","vente":"#10b981"},
                          labels={"price_per_m2":"DH/m²","city":"Ville"})
        fig3.update_layout(**PLOTLY_THEME, height=320,
                           legend=dict(orientation="h", yanchor="bottom",
                                       y=1.02, x=0, font_color="#94a3b8"))
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown('<div class="section-header">Répartition des annonces par source</div>',
                    unsafe_allow_html=True)
        col_s1, col_s2 = st.columns([2, 3])
        with col_s1:
            sc = df["source"].value_counts().reset_index()
            sc.columns = ["source", "count"]
            fig4 = px.pie(sc, names="source", values="count",
                          color_discrete_sequence=COLORS, hole=0.55)
            fig4.update_layout(**PLOTLY_THEME, height=300,
                               legend=dict(font_color="#94a3b8"))
            fig4.update_traces(textfont_color="#f1f5f9", marker_line_width=0)
            st.plotly_chart(fig4, use_container_width=True)
        with col_s2:
            sp = (df.dropna(subset=["price_per_m2"])
                  .groupby(["city","source"])["price_per_m2"]
                  .median().reset_index())
            fig5 = px.bar(sp, x="city", y="price_per_m2", color="source",
                          barmode="group", color_discrete_sequence=COLORS,
                          labels={"price_per_m2":"DH/m² médian","city":"Ville"})
            fig5.update_layout(**PLOTLY_THEME, height=300,
                               legend=dict(orientation="h", yanchor="bottom",
                                           y=1.02, x=0, font_color="#94a3b8"))
            st.plotly_chart(fig5, use_container_width=True)

# ══ TAB 2 — RPPI ══════════════════════════════════════════
with t2:
    bp = PROJECT.get('base_period','2024-Q1')
    st.markdown(f"""
    <div style="background:#172554; border:1px solid #1d4ed8; border-radius:10px;
                padding:16px 20px; margin-bottom:20px;">
        <div style="font-size:12px; color:#93c5fd; font-weight:600;
                    text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">
            Méthode — Time Dummy Hédonique
        </div>
        <div style="font-size:13px; color:#bfdbfe; line-height:1.7;">
            RPPI(t) = 100 × exp(γ<sub>t</sub>) où γ<sub>t</sub> est le coefficient temporel
            du modèle semi-log OLS · Période de base : <b>{bp} = 100</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    idx = load_index()
    idx_f = idx[idx["city"].isin(sel_cities)] if sel_cities and not idx.empty else idx

    if idx_f.empty:
        st.markdown("""
        <div style="background:#1c1917; border:1px solid #292524; border-radius:10px;
                    padding:40px; text-align:center;">
            <div style="font-size:32px; margin-bottom:12px;">📊</div>
            <div style="font-size:15px; color:#78716c; margin-bottom:8px;">
                Indice pas encore calculé
            </div>
            <code style="color:#f59e0b; font-size:13px;">python main.py --hedonic</code>
            <span style="color:#78716c; font-size:13px;"> puis </span>
            <code style="color:#f59e0b; font-size:13px;">python main.py --index</code>
        </div>
        """, unsafe_allow_html=True)
    else:
        for txn in ["location","vente"]:
            sub = idx_f[idx_f["transaction"]==txn].sort_values("year_quarter")
            if sub.empty:
                continue
            label = "Location" if txn == "location" else "Vente"
            color = "#3b82f6" if txn == "location" else "#10b981"
            st.markdown(f'<div class="section-header">RPPI — {label}</div>',
                        unsafe_allow_html=True)

            # Latest index per city
            latest = sub.groupby("city")["index_value"].last().reset_index()
            kpi_cols = st.columns(len(latest))
            for i, (_, row) in enumerate(latest.iterrows()):
                delta = row.index_value - 100
                delta_str = f"+{delta:.1f}pt" if delta >= 0 else f"{delta:.1f}pt"
                delta_color = "#22c55e" if delta >= 0 else "#ef4444"
                with kpi_cols[i]:
                    st.markdown(f"""<div class="kpi-card">
                        <div style="font-size:11px;color:#475569;margin-bottom:4px;">
                            {row.city.title()}
                        </div>
                        <div style="font-size:24px;font-weight:700;color:{color};">
                            {row.index_value:.1f}
                        </div>
                        <div style="font-size:11px;color:{delta_color};">
                            {delta_str} vs base 100
                        </div>
                    </div>""", unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_hline(y=100, line_dash="dot", line_color="#334155",
                          annotation_text="Base 100", annotation_font_color="#475569")
            for i, city in enumerate(sub["city"].unique()):
                city_df = sub[sub["city"]==city]
                fig.add_trace(go.Scatter(
                    x=city_df["year_quarter"], y=city_df["index_value"],
                    name=city.title(), mode="lines+markers",
                    line=dict(color=COLORS[i % len(COLORS)], width=2.5),
                    marker=dict(size=7, symbol="circle"),
                ))
            fig.update_layout(**PLOTLY_THEME, height=350,
                              yaxis_title="Indice (base 100)",
                              legend=dict(orientation="h", yanchor="bottom",
                                          y=1.02, font_color="#94a3b8"))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)

# ══ TAB 3 — EDA ══════════════════════════════════════════
with t3:
    if df.empty:
        st.warning("Aucune donnée.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Distribution des loyers par ville</div>',
                        unsafe_allow_html=True)
            rd = df[df["transaction"]=="location"].dropna(subset=["price"])
            if not rd.empty:
                fig = px.histogram(rd, x="price", color="city", nbins=35,
                                   color_discrete_sequence=COLORS,
                                   labels={"price":"DH/mois","count":"Annonces"})
                fig.update_layout(**PLOTLY_THEME, height=300,
                                  barmode="overlay",
                                  legend=dict(font_color="#94a3b8"))
                fig.update_traces(opacity=0.75, marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown('<div class="section-header">Prix de vente au m² par ville</div>',
                        unsafe_allow_html=True)
            sd = df[df["transaction"]=="vente"].dropna(subset=["price_per_m2"])
            if not sd.empty:
                fig2 = px.histogram(sd, x="price_per_m2", color="city", nbins=35,
                                    color_discrete_sequence=COLORS,
                                    labels={"price_per_m2":"DH/m²","count":"Annonces"})
                fig2.update_layout(**PLOTLY_THEME, height=300,
                                   barmode="overlay",
                                   legend=dict(font_color="#94a3b8"))
                fig2.update_traces(opacity=0.75, marker_line_width=0)
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-header">Corrélation Prix vs Surface (avec tendance OLS)</div>',
                    unsafe_allow_html=True)
        sc = df.dropna(subset=["price","surface"])
        fig3 = px.scatter(sc, x="surface", y="price", color="city",
                          facet_col="transaction", opacity=0.45,
                          trendline="ols",
                          color_discrete_sequence=COLORS,
                          labels={"surface":"Surface (m²)","price":"Prix (DH)"})
        fig3.update_layout(**PLOTLY_THEME, height=360,
                           legend=dict(font_color="#94a3b8"))
        fig3.update_traces(marker_size=5, marker_line_width=0)
        st.plotly_chart(fig3, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="section-header">Nombre d\'annonces par ville</div>',
                        unsafe_allow_html=True)
            vc = df.groupby(["city","transaction"]).size().reset_index(name="n")
            fig4 = px.bar(vc, x="city", y="n", color="transaction",
                          barmode="group", color_discrete_map={
                              "location":"#3b82f6","vente":"#10b981"},
                          labels={"n":"Annonces","city":"Ville"})
            fig4.update_layout(**PLOTLY_THEME, height=280,
                               legend=dict(font_color="#94a3b8"))
            fig4.update_traces(marker_line_width=0)
            st.plotly_chart(fig4, use_container_width=True)

        with c4:
            st.markdown('<div class="section-header">Score de qualité par ville</div>',
                        unsafe_allow_html=True)
            qc = df.groupby("city")["quality_score"].mean().reset_index()
            fig5 = px.bar(qc, x="city", y="quality_score",
                          color="quality_score",
                          color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                          range_color=[0.5, 1.0],
                          labels={"quality_score":"Score moyen","city":"Ville"})
            fig5.update_layout(**PLOTLY_THEME, height=280,
                               coloraxis_showscale=False)
            fig5.update_traces(marker_line_width=0)
            st.plotly_chart(fig5, use_container_width=True)

# ══ TAB 4 — MAP ══════════════════════════════════════════
with t4:
    st.markdown('<div class="section-header">Carte des prix médians par ville</div>',
                unsafe_allow_html=True)

    m = folium.Map(location=[31.7917, -7.0926], zoom_start=5,
                   tiles="CartoDB dark_matter")

    city_stats = (df.groupby("city")
                  .agg(median_price=("price","median"),
                       count=("price","count"),
                       avg_ppm2=("price_per_m2","median"))
                  .reset_index())

    for _, row in city_stats.iterrows():
        coords = CITIES.get(row["city"])
        if not coords:
            continue
        lat, lon = coords["lat"], coords["lon"]
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:160px'>
            <b style='font-size:14px'>{row['city'].title()}</b><br>
            <hr style='margin:4px 0'>
            Prix médian: <b>{row['median_price']:,.0f} DH</b><br>
            Prix/m²: <b>{row['avg_ppm2']:,.0f} DH/m²</b><br>
            Annonces: <b>{row['count']:,}</b>
        </div>"""
        radius = min(max(int(row["count"] / 5), 12), 50)
        folium.CircleMarker(
            location=(lat, lon), radius=radius,
            color="#3b82f6", fill=True,
            fill_color="#3b82f6", fill_opacity=0.5,
            weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"<b>{row['city'].title()}</b> — {row['median_price']:,.0f} DH",
        ).add_to(m)

    st_folium(m, width=None, height=520)

    st.markdown('<div class="section-header" style="margin-top:16px">Prix/m² par ville</div>',
                unsafe_allow_html=True)
    map_bar = city_stats.sort_values("avg_ppm2", ascending=True)
    fig_map = px.bar(map_bar, x="avg_ppm2", y="city", orientation="h",
                     color="avg_ppm2",
                     color_continuous_scale=["#1e40af","#3b82f6","#93c5fd"],
                     labels={"avg_ppm2":"DH/m² médian","city":""})
    fig_map.update_layout(**PLOTLY_THEME, height=260, coloraxis_showscale=False)
    fig_map.update_traces(marker_line_width=0)
    st.plotly_chart(fig_map, use_container_width=True)

# ══ TAB 5 — DATA ══════════════════════════════════════════
with t5:
    if df.empty:
        st.warning("Aucune donnée.")
    else:
        search_col, dl_col = st.columns([3, 1])
        with search_col:
            search = st.text_input("Rechercher dans les titres...",
                                   placeholder="ex: appartement rabat",
                                   label_visibility="collapsed")
        with dl_col:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Télécharger CSV", data=csv,
                               file_name=f"rppi_{datetime.today().strftime('%Y%m%d')}.csv",
                               mime="text/csv", use_container_width=True)

        show_df = df.copy()
        if search:
            mask = show_df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)
            show_df = show_df[mask]

        cols = ["city","transaction","property_type","price",
                "surface","price_per_m2","rooms","quality_score","year_quarter"]
        st.dataframe(
            show_df[cols].sort_values("price", ascending=False)
                         .reset_index(drop=True),
            use_container_width=True, height=520,
            column_config={
                "city":          st.column_config.TextColumn("Ville"),
                "transaction":   st.column_config.TextColumn("Transaction"),
                "property_type": st.column_config.TextColumn("Type"),
                "price":         st.column_config.NumberColumn("Prix (DH)", format="%,.0f"),
                "surface":       st.column_config.NumberColumn("Surface (m²)", format="%.0f"),
                "price_per_m2":  st.column_config.NumberColumn("Prix/m²", format="%,.0f"),
                "rooms":         st.column_config.NumberColumn("Pièces", format="%d"),
                "quality_score": st.column_config.ProgressColumn("Qualité", min_value=0, max_value=1),
                "year_quarter":  st.column_config.TextColumn("Période"),
            }
        )
        st.caption(f"{len(show_df):,} enregistrements affichés sur {len(df):,}")

# ══ TAB 6 — METHODOLOGY ══════════════════════════════════
with t6:
    col_m1, col_m2 = st.columns([3, 2])
    with col_m1:
        bp = PROJECT.get('base_period','2024-Q1')
        st.markdown(f"""
        <div style="background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:24px; margin-bottom:16px;">
            <div style="font-size:11px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.08em; margin-bottom:12px;">Formule du modèle hédonique</div>
            <div style="background:#1e293b; border-radius:8px; padding:16px; margin-bottom:16px;
                        font-family:monospace; font-size:15px; color:#93c5fd; text-align:center;">
                ln(P<sub>it</sub>) = α + β·X<sub>it</sub> + Σγ<sub>t</sub>·D<sub>t</sub> + ε<sub>it</sub>
            </div>
            <table style="width:100%; font-size:12px; border-collapse:collapse;">
                <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:6px; color:#3b82f6; font-family:monospace; width:100px;">ln(P_it)</td>
                    <td style="padding:6px; color:#94a3b8;">Log du prix de l'annonce i à la période t</td>
                </tr>
                <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:6px; color:#3b82f6; font-family:monospace;">β·X_it</td>
                    <td style="padding:6px; color:#94a3b8;">Effet des caractéristiques structurelles</td>
                </tr>
                <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:6px; color:#f59e0b; font-family:monospace;">γ_t·D_t</td>
                    <td style="padding:6px; color:#94a3b8;">Effet temporel → devient le RPPI</td>
                </tr>
                <tr>
                    <td style="padding:6px; color:#10b981; font-family:monospace;">RPPI_t</td>
                    <td style="padding:6px; color:#94a3b8;">100 × exp(γ_t) · Période de base: {bp} = 100</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div style="background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:24px;">
            <div style="font-size:11px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.08em; margin-bottom:16px;">Fiche projet</div>
            <div style="font-size:13px; line-height:2; color:#94a3b8;">
                <b style="color:#f1f5f9;">Projet</b><br>{PROJECT['name']}<br><br>
                <b style="color:#f1f5f9;">Périmètre</b><br>{PROJECT['scope']}<br><br>
                <b style="color:#f1f5f9;">Statut</b><br>{PROJECT['type']}<br><br>
                <b style="color:#f1f5f9;">Audience</b><br>{PROJECT['audience']}<br><br>
                <b style="color:#f1f5f9;">Fréquence</b><br>Quotidienne (collecte) · Mensuelle (indice)<br><br>
                <b style="color:#f1f5f9;">Référence</b><br>{PROJECT['reference']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Références officielles</div>',
                unsafe_allow_html=True)
    refs = [
        ("FMI 2013", "Handbook on Residential Property Price Indices", "#3b82f6"),
        ("Eurostat 2013", "Handbook on Residential Property Price Indices", "#10b981"),
        ("OCDE 2020", "Residential Property Price Indicators", "#f59e0b"),
        ("UNECE 2019", "Guidelines on Web Scraping for Official Statistics", "#8b5cf6"),
        ("HCP Maroc", "Direction de la Statistique · Rabat", "#ec4899"),
    ]
    ref_cols = st.columns(len(refs))
    for i, (org, title, color) in enumerate(refs):
        with ref_cols[i]:
            st.markdown(f"""
            <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px;
                        padding:12px; text-align:center; height:90px;">
                <div style="font-size:13px; font-weight:700; color:{color};
                            margin-bottom:4px;">{org}</div>
                <div style="font-size:10px; color:#475569; line-height:1.5;">{title}</div>
            </div>
            """, unsafe_allow_html=True)

# ══ TAB 7 — SOURCES ═══════════════════════════════════════
with t7:
    if df.empty:
        st.warning("Aucune donnée.")
    else:
        st.markdown('<div class="section-header">Comparaison des sources de données</div>',
                    unsafe_allow_html=True)

        # KPI row: listing count per source
        src_counts = df["source"].value_counts()
        kpi_cols = st.columns(len(src_counts) + 1)
        with kpi_cols[0]:
            st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value">{len(df):,}</div>
                <div class="kpi-label">Total (filtré)</div>
            </div>""", unsafe_allow_html=True)
        for i, (src, n) in enumerate(src_counts.items(), start=1):
            with kpi_cols[i]:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-value">{n:,}</div>
                    <div class="kpi-label">{src.capitalize()}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Annonces par ville et par source**")
            city_src = df.groupby(["city", "source"]).size().reset_index(name="count")
            fig_bar = px.bar(city_src, x="city", y="count", color="source",
                              barmode="group", color_discrete_sequence=COLORS)
            fig_bar.update_layout(**PLOTLY_THEME, height=340)
            st.plotly_chart(fig_bar, use_container_width=True)

        with c2:
            st.markdown("**Distribution du prix/m² par source**")
            box_df = df.dropna(subset=["price_per_m2"])
            fig_box = px.box(box_df, x="source", y="price_per_m2", color="source",
                              color_discrete_sequence=COLORS, points=False)
            fig_box.update_layout(**PLOTLY_THEME, height=340)
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Prix moyen au m² par ville et par source**")
        pivot = (df.dropna(subset=["price_per_m2"])
                   .groupby(["city", "source"])["price_per_m2"]
                   .mean().round(0).unstack("source"))
        st.dataframe(pivot, use_container_width=True)
        st.caption("Un écart important entre sources sur une même ville peut indiquer "
                   "un biais de sélection propre à la plateforme (ex. Agenz = davantage "
                   "d'annonces d'agences vérifiées, Mubawab = davantage de particuliers).")