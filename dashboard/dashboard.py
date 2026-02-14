"""
Medical Telegram Warehouse - Interactive Dashboard
Market Intelligence Platform for Ethiopian Pharmaceutical Channels
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from typing import Optional

# Page configuration
st.set_page_config(
    page_title="Medical Telegram Warehouse",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"


# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


def fetch_api_data(endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
    """Fetch data from API endpoint."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def main():
    """Main dashboard application."""
    
    # Header
    st.markdown('<div class="main-header">🏥 Medical Telegram Warehouse</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Market Intelligence Platform for Ethiopian Pharmaceutical Channels</div>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["📊 Overview", "🔍 Product Analysis", "📈 Channel Activity", "🖼️ Visual Content", "🔎 Search Messages"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "This dashboard provides real-time market intelligence from Ethiopian medical Telegram channels. "
        "Track product mentions, channel activity, and visual content trends."
    )
    
    # Main content based on selected page
    if page == "📊 Overview":
        show_overview()
    elif page == "🔍 Product Analysis":
        show_product_analysis()
    elif page == "📈 Channel Activity":
        show_channel_activity()
    elif page == "🖼️ Visual Content":
        show_visual_content()
    elif page == "🔎 Search Messages":
        show_message_search()


def show_overview():
    """Display overview dashboard."""
    st.header("📊 Market Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Channels Monitored",
            value="5+",
            delta="Active"
        )
    
    with col2:
        st.metric(
            label="Messages Processed",
            value="50K+",
            delta="+2.5K this week"
        )
    
    with col3:
        st.metric(
            label="Images Analyzed",
            value="10K+",
            delta="+500 this week"
        )
    
    with col4:
        st.metric(
            label="Data Coverage",
            value="100%",
            delta="Real-time"
        )
    
    st.markdown("---")
    
    # Top products preview
    st.subheader("🔝 Top Mentioned Products")
    top_products = fetch_api_data("/api/reports/top-products", {"limit": 10})
    
    if top_products:
        df = pd.DataFrame(top_products)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.bar(
                df,
                x="count",
                y="term",
                orientation="h",
                title="Top 10 Most Mentioned Terms",
                labels={"count": "Mentions", "term": "Product/Term"},
                color="count",
                color_continuous_scale="Blues"
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(df, use_container_width=True, height=400)


def show_product_analysis():
    """Display product analysis page."""
    st.header("🔍 Product Analysis")
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        limit = st.slider("Number of products to display", 5, 50, 20)
    with col2:
        st.markdown("")  # Spacing
    
    # Fetch data
    data = fetch_api_data("/api/reports/top-products", {"limit": limit})
    
    if data:
        df = pd.DataFrame(data)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart
            fig_bar = px.bar(
                df.head(15),
                x="count",
                y="term",
                orientation="h",
                title=f"Top {min(15, len(df))} Products by Mentions",
                labels={"count": "Number of Mentions", "term": "Product/Term"},
                color="count",
                color_continuous_scale="Viridis"
            )
            fig_bar.update_layout(height=500)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            # Pie chart
            fig_pie = px.pie(
                df.head(10),
                values="count",
                names="term",
                title="Market Share - Top 10 Products",
                hole=0.4
            )
            fig_pie.update_layout(height=500)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Data table
        st.subheader("📋 Detailed Product Mentions")
        st.dataframe(
            df.style.background_gradient(subset=["count"], cmap="Blues"),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"product_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def show_channel_activity():
    """Display channel activity page."""
    st.header("📈 Channel Activity Analysis")
    
    # Channel selector
    channels = ["CheMed123", "lobelia4cosmetics", "tikvahpharma", "ethiopharmaceutical", "yenehealth"]
    selected_channel = st.selectbox("Select Channel", channels)
    
    # Fetch data
    data = fetch_api_data(f"/api/channels/{selected_channel}/activity")
    
    if data:
        df = pd.DataFrame(data)
        df["post_date"] = pd.to_datetime(df["post_date"])
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Messages",
                f"{df['message_count'].sum():,}",
                f"Last 30 days"
            )
        
        with col2:
            st.metric(
                "Avg Daily Messages",
                f"{df['message_count'].mean():.1f}",
                f"±{df['message_count'].std():.1f}"
            )
        
        with col3:
            st.metric(
                "Avg Views per Message",
                f"{df['avg_views'].mean():,.0f}",
                f"Peak: {df['avg_views'].max():,.0f}"
            )
        
        # Time series chart
        st.subheader("📅 Daily Activity Trend")
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df["post_date"],
            y=df["message_count"],
            mode="lines+markers",
            name="Messages",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title=f"Daily Message Volume - {selected_channel}",
            xaxis_title="Date",
            yaxis_title="Number of Messages",
            hovermode="x unified",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Views trend
        st.subheader("👁️ Average Views Trend")
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            x=df["post_date"],
            y=df["avg_views"],
            name="Avg Views",
            marker_color="#2ca02c"
        ))
        
        fig2.update_layout(
            title=f"Average Views per Message - {selected_channel}",
            xaxis_title="Date",
            yaxis_title="Average Views",
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Data table
        st.subheader("📊 Activity Data")
        st.dataframe(df.sort_values("post_date", ascending=False), use_container_width=True)


def show_visual_content():
    """Display visual content analysis page."""
    st.header("🖼️ Visual Content Analysis")
    
    # Fetch data
    data = fetch_api_data("/api/reports/visual-content")
    
    if data:
        df = pd.DataFrame(data)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Images", f"{df['total_images'].sum():,}")
        
        with col2:
            st.metric("Promotional", f"{df['promotional_count'].sum():,}")
        
        with col3:
            st.metric("Product Display", f"{df['product_display_count'].sum():,}")
        
        with col4:
            st.metric("Lifestyle", f"{df['lifestyle_count'].sum():,}")
        
        st.markdown("---")
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Images by channel
            fig1 = px.bar(
                df.sort_values("total_images", ascending=False),
                x="channel_name",
                y="total_images",
                title="Total Images by Channel",
                labels={"total_images": "Number of Images", "channel_name": "Channel"},
                color="total_images",
                color_continuous_scale="Blues"
            )
            fig1.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Visual percentage
            fig2 = px.bar(
                df.sort_values("visual_percentage", ascending=False),
                x="channel_name",
                y="visual_percentage",
                title="Visual Content Percentage by Channel",
                labels={"visual_percentage": "Percentage (%)", "channel_name": "Channel"},
                color="visual_percentage",
                color_continuous_scale="Greens"
            )
            fig2.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Category breakdown
        st.subheader("📊 Image Category Breakdown")
        
        category_data = pd.DataFrame({
            "Category": ["Promotional", "Product Display", "Lifestyle", "Other"],
            "Count": [
                df["promotional_count"].sum(),
                df["product_display_count"].sum(),
                df["lifestyle_count"].sum(),
                df["other_count"].sum()
            ]
        })
        
        fig3 = px.pie(
            category_data,
            values="Count",
            names="Category",
            title="Overall Image Category Distribution",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)
        
        # Detailed table
        st.subheader("📋 Detailed Channel Statistics")
        st.dataframe(df, use_container_width=True)


def show_message_search():
    """Display message search page."""
    st.header("🔎 Search Messages")
    
    # Search controls
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input("Enter search term (minimum 3 characters)", "")
    
    with col2:
        limit = st.number_input("Results limit", min_value=1, max_value=100, value=20)
    
    if st.button("🔍 Search", type="primary") and len(search_query) >= 3:
        # Fetch data
        data = fetch_api_data("/api/search/messages", {"query": search_query, "limit": limit})
        
        if data:
            st.success(f"Found {len(data)} messages containing '{search_query}'")
            
            df = pd.DataFrame(data)
            
            # Display results
            for idx, row in df.iterrows():
                with st.expander(f"📝 {row['channel_name']} - {row['message_timestamp']} (Views: {row['view_count']})"):
                    st.write(f"**Message ID:** {row['message_id']}")
                    st.write(f"**Channel:** {row['channel_name']}")
                    st.write(f"**Date:** {row['message_timestamp']}")
                    st.write(f"**Views:** {row['view_count']:,}")
                    st.markdown("---")
                    st.write(row['message_text'][:500] + ("..." if len(row['message_text']) > 500 else ""))
            
            # Download results
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Search Results",
                data=csv,
                file_name=f"search_{search_query}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning(f"No messages found containing '{search_query}'")
    
    elif search_query and len(search_query) < 3:
        st.warning("Please enter at least 3 characters to search")


if __name__ == "__main__":
    main()
